<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import { user, chatContext } from '$lib/stores';

	import { getCourses, getLabsForCourse } from '$lib/apis/courses';
	import { getLabById } from '$lib/apis/labs';
	import { getKnowledgeById } from '$lib/apis/knowledge';

	import Files from '$lib/components/workspace/Knowledge/KnowledgeBase/Files.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	// URL ?lab_id=...
	let queryLabId: string | null = null;
	$: queryLabId = $page.url.searchParams.get('lab_id');

	// Lab / knowledge state
	let labId: string | null = null;
	let lab: any = null;
	let knowledge: any = null;
	let files: any[] = [];
	let loading = true;

	// Admin-only picker state
	let courses: any[] = [];
	let selectedCourseId: string | null = null;
	let labsForCourse: any[] = [];
	let selectedPickerLabId: string | null = null;

	// Avoid redundant loads when labId doesn't actually change
	let lastLoadedLabId: string | null = null;

	// Preview modal state
	let selectedFileId: string | null = null;
	let previewUrl: string | null = null; // for iframe-type previews
	let previewText = ''; // for text previews (.sp, .cir, .txt, etc.)
	let previewMode: 'iframe' | 'text' | null = null;
	let loadingPreview = false;

	function clearPreview() {
		previewUrl = null;
		previewText = '';
		previewMode = null;
		selectedFileId = null;
		loadingPreview = false;
	}

	onDestroy(clearPreview);

	// Current lab:
	//  - URL ?lab_id=... overrides
	//  - otherwise use chatContext (lab chat)
	$: labId = (queryLabId as string | null) ?? ($chatContext?.lab_id ?? null);

	// Admin: ensure course list exists whenever there is no active lab
	$: if (browser && !labId && $user?.role === 'admin' && courses.length === 0) {
		(async () => {
			try {
				loading = true;
				await loadCourses();
			} catch (e) {
				console.error(e);
				toast.error(`${e}`);
			} finally {
				loading = false;
			}
		})();
	}

	// Load lab + knowledge + files whenever labId changes
	$: if (browser && labId && labId !== lastLoadedLabId) {
		lastLoadedLabId = labId;
		clearPreview();

		(async () => {
			try {
				loading = true;

				lab = await getLabById(localStorage.token, labId);

				if (!lab?.knowledge_id) {
					knowledge = null;
					files = [];
					toast.error('No knowledge collection is linked to this lab.');
					return;
				}

				knowledge = await getKnowledgeById(localStorage.token, lab.knowledge_id);
				files = Array.isArray(knowledge?.files) ? knowledge.files : [];
			} catch (e) {
				console.error(e);
				toast.error(`${e}`);
			} finally {
				loading = false;
			}
		})();
	} else if (browser && !labId) {
		lastLoadedLabId = null;
		lab = null;
		knowledge = null;
		files = [];
		clearPreview();
	}

	async function loadCourses() {
		if (!browser) return;
		try {
			const res = await getCourses(localStorage.token);
			courses = Array.isArray(res) ? res : res?.items ?? [];
		} catch (e) {
			console.error(e);
			toast.error(`${e}`);
		}
	}

	async function onSelectCourse(courseId: string) {
		selectedCourseId = courseId || null;
		selectedPickerLabId = null;
		labsForCourse = [];
		if (!selectedCourseId || !browser) return;

		try {
			const res = await getLabsForCourse(localStorage.token, selectedCourseId);
			labsForCourse = Array.isArray(res) ? res : res?.items ?? res ?? [];
		} catch (e) {
			console.error(e);
			toast.error(`${e}`);
		}
	}

	function handleCourseChange(e: Event) {
		const select = e.target as HTMLSelectElement;
		onSelectCourse(select.value);
	}

	function handleLabChange(e: Event) {
		const select = e.target as HTMLSelectElement;
		selectedPickerLabId = select.value;
	}

	function goToSelectedLab() {
		if (!selectedPickerLabId) return;
		goto(`/workspace/lab-resources?lab_id=${encodeURIComponent(selectedPickerLabId)}`);
	}

	// PDFs & images → iframe; everything else (including .sp) → text preview
	async function openPreview(file: any) {
		if (!browser || !file?.id) return;

		clearPreview();
		selectedFileId = file.id;

		const name: string = file.filename || file.name || '';
		const ext = (name.split('.').pop() || '').toLowerCase();

		const mime =
			(file.meta?.content_type ||
				file.data?.content_type ||
				file.mime_type ||
				'')?.toLowerCase?.() || '';

		const pdfLike = mime.includes('pdf') || ext === 'pdf';

		const imageExts = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'svg', 'webp'];
		const imageLike = mime.startsWith('image/') || imageExts.includes(ext);

		try {
			loadingPreview = true;
			const contentUrl = `${WEBUI_BASE_URL}/api/v1/files/${file.id}/content`;

			if (pdfLike || imageLike) {
				// PDFs & images → embed in iframe
				previewUrl = contentUrl;
				previewMode = 'iframe';
			} else {
				// Everything else → fetch as text and render in <pre>
				const res = await fetch(contentUrl, {
					method: 'GET',
					headers: {
						authorization: `Bearer ${localStorage.token}`
					}
				});

				if (!res.ok) {
					const errText = await res.text().catch(() => '');
					throw new Error(errText || `Failed to load file (${res.status})`);
				}

				previewText = await res.text();
				previewMode = 'text';
			}
		} catch (e) {
			console.error(e);
			toast.error(`${e}`);
			clearPreview();
		} finally {
			loadingPreview = false;
		}
	}

	function handleFileClick(event: CustomEvent<any>) {
		const detail = event.detail;
		let file: any | null = null;

		if (!detail) return;

		if (typeof detail === 'string') {
			file = files.find((f) => f.id === detail) ?? null;
		} else if (detail.file) {
			file = detail.file;
		} else if (detail.id) {
			file = detail;
		}

		if (!file) return;
		void openPreview(file);
	}

	// Download helper (auth fetch → blob)
	async function downloadFile(file: any) {
		if (!browser) return;
		try {
			const base = import.meta.env.VITE_WEBUI_API_BASE_URL || '';
			const filename = encodeURIComponent(file.filename || file.name || 'download');
			const url = `${base}/files/${file.id}/content/${filename}`;
			const res = await fetch(url, {
				method: 'GET',
				headers: {
					Accept: 'application/json',
					authorization: `Bearer ${localStorage.token}`
				}
			});
			if (!res.ok) throw await res.json();
			const blob = await res.blob();
			const a = document.createElement('a');
			a.href = URL.createObjectURL(blob);
			a.download = file.filename || file.name || 'download';
			a.click();
			URL.revokeObjectURL(a.href);
		} catch (e) {
			console.error(e);
			toast.error(`${e}`);
		}
	}
</script>

<svelte:head>
	<title>Lab Resources • Workspace</title>
</svelte:head>

<div class="p-4 max-w-5xl mx-auto w-full">
	<div class="flex items-center justify-between mb-3">
		<h1 class="text-xl font-semibold">
			{$i18n.t('Lab Resources')}
		</h1>

		{#if lab}
			<div class="text-sm text-neutral-500">
				{lab?.course_id?.toUpperCase?.() || ''} • {lab?.name || ''}
			</div>
		{/if}
	</div>

	{#if $user?.role === 'admin' && lab?.id}
		<div class="mb-3 flex justify-end">
			<button
				class="text-xs px-3 py-1 rounded-md border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800 disabled:opacity-50"
				on:click={() => goto(`/workspace/knowledge?lab_id=${encodeURIComponent(lab.id)}`)}
			>
				{$i18n.t('Open in Knowledge Editor')}
			</button>
		</div>
	{/if}

	{#if loading}
		<div class="text-neutral-500 text-sm">{$i18n.t('Loading')}…</div>
	{:else if !labId}
		<!-- Student: message; Admin: Course/Lab picker -->
		{#if $user?.role !== 'admin'}
			<div class="text-neutral-500 text-sm">
				{$i18n.t('Open Lab Resources from a lab page to view that lab’s materials.')}
			</div>
		{:else}
			<div class="space-y-3">
				<div class="text-sm text-neutral-600 dark:text-neutral-300">
					{$i18n.t('Pick a Course and Lab to view resources')}
				</div>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
					<div>
						<label class="block text-xs mb-1">{$i18n.t('Course')}</label>
						<select
							class="w-full rounded-lg border px-3 py-2 bg-transparent"
							on:change={handleCourseChange}
						>
							<option value="">{ $i18n.t('Select a course') }</option>
							{#each courses as c}
								<option value={c.id}>
									{c.code || c.name} {c.title ? `• ${c.title}` : ''}
								</option>
							{/each}
						</select>
					</div>

					<div>
						<label class="block text-xs mb-1">{$i18n.t('Lab')}</label>
						<select
							class="w-full rounded-lg border px-3 py-2 bg-transparent"
							disabled={!selectedCourseId || labsForCourse.length === 0}
							on:change={handleLabChange}
						>
							<option value="">{ $i18n.t('Select a lab') }</option>
							{#each labsForCourse as l}
								<option value={l.id}>{l.name}</option>
							{/each}
						</select>
					</div>
				</div>

				<div>
					<button
						class="px-3 py-1.5 text-sm rounded-lg border hover:bg-neutral-50 dark:hover:bg-neutral-800 disabled:opacity-60"
						on:click={goToSelectedLab}
						disabled={!selectedPickerLabId}
					>
						{$i18n.t('Open resources')}
					</button>
				</div>
			</div>
		{/if}
	{:else if files?.length === 0}
		<div class="text-neutral-500 text-sm">
			{$i18n.t('No files have been added yet.')}
		</div>
	{:else}
		<div class="max-h-[70vh] overflow-y-auto border rounded-lg p-2">
			<Files
				{files}
				selectedFileId={selectedFileId}
				on:click={handleFileClick}
				on:delete={() => { /* read-only here; edits happen in Knowledge */ }}
			/>
		</div>

		<div class="mt-3 text-xs text-neutral-500">
			{$i18n.t('Click a file to preview or use the download action.')}
		</div>
	{/if}

	{#if previewMode || loadingPreview}
		<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
			<div class="bg-white dark:bg-neutral-900 rounded-xl shadow-xl max-w-5xl w-[90%] h-[80vh] flex flex-col">
				<!-- Header -->
				<div class="flex items-center justify-between px-4 py-2 border-b border-neutral-200 dark:border-neutral-800">
					<div class="text-sm font-medium truncate">
						{#if selectedFileId}
							{#each files as f}
								{#if f.id === selectedFileId}
									{f.filename || f.name || $i18n.t('File preview')}
								{/if}
							{/each}
						{:else}
							{$i18n.t('File preview')}
						{/if}
					</div>
					<button
						class="text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-100 text-xl leading-none px-2"
						on:click={clearPreview}
						aria-label="Close preview"
					>
						×
					</button>
				</div>

				<!-- Body -->
				<div class="flex-1 min-h-0">
					{#if loadingPreview && !previewMode}
						<div class="w-full h-full flex items-center justify-center text-neutral-500 text-sm">
							{$i18n.t('Loading preview')}…
						</div>
					{:else if previewMode === 'iframe' && previewUrl}
						<iframe
							src={previewUrl}
							class="w-full h-full rounded-b-xl"
						/>
					{:else if previewMode === 'text'}
						<pre class="w-full h-full overflow-auto text-xs font-mono whitespace-pre p-3">
{previewText}
						</pre>
					{:else}
						<div class="w-full h-full flex items-center justify-center text-neutral-500 text-sm">
							{$i18n.t('Unable to preview this file.')}
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>
