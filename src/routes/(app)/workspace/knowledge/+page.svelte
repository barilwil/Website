<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import { user } from '$lib/stores';
	import { getCourses, getLabsForCourse } from '$lib/apis/courses';
	import { getLabById } from '$lib/apis/labs';
	import KnowledgeBase from '$lib/components/workspace/Knowledge/KnowledgeBase.svelte';

	const i18n = getContext('i18n');

	let loading = true;

	let courses: any[] = [];
	let labsForCourse: any[] = [];
	let selectedCourseId: string | null = null;
	let selectedLabId: string | null = null;
	let selectedLab: any = null;
	let selectedKnowledgeId: string | null = null;

	onMount(async () => {
		// Extra safety: students should never get here
		if ($user?.role !== 'admin') {
			goto('/assistant');
			return;
		}

		try {
			const res = await getCourses(localStorage.token);
			courses = Array.isArray(res) ? res : (res?.items ?? res ?? []);

			// Optional deep link: /workspace/knowledge?lab_id=...
			const labIdFromQuery = $page.url.searchParams.get('lab_id');

			if (labIdFromQuery) {
				await preselectLab(labIdFromQuery);
			}
		} catch (e) {
			console.error(e);
			toast.error(`${e}`);
		} finally {
			loading = false;
		}
	});

	async function preselectLab(labId: string) {
		try {
			const lab = await getLabById(localStorage.token, labId);
			if (!lab) return;

			selectedLabId = lab.id;
			selectedLab = lab;
			selectedKnowledgeId = lab.knowledge_id ?? null;

			selectedCourseId = lab.course_id ?? null;
			if (selectedCourseId) {
				const labsRes = await getLabsForCourse(localStorage.token, selectedCourseId);
				labsForCourse = Array.isArray(labsRes) ? labsRes : (labsRes?.items ?? labsRes ?? []);
			}
		} catch (e) {
			console.error(e);
			toast.error(`${e}`);
		}
	}

	async function handleCourseChange(event: Event) {
		const select = event.target as HTMLSelectElement;
		selectedCourseId = select.value || null;
		selectedLabId = null;
		selectedLab = null;
		selectedKnowledgeId = null;
		labsForCourse = [];

		if (!selectedCourseId) return;

		try {
			const res = await getLabsForCourse(localStorage.token, selectedCourseId);
			labsForCourse = Array.isArray(res) ? res : (res?.items ?? res ?? []);
		} catch (e) {
			console.error(e);
			toast.error(`${e}`);
		}
	}

	function handleLabChange(event: Event) {
		const select = event.target as HTMLSelectElement;
		const labId = select.value || null;
		selectedLabId = labId;
		selectedLab = labsForCourse.find((lab) => lab.id === labId) ?? null;
		selectedKnowledgeId = selectedLab?.knowledge_id ?? null;
	}

	function openStudentView() {
		if (!selectedLabId) return;
		goto(`/workspace/lab-resources?lab_id=${encodeURIComponent(selectedLabId)}`);
	}
</script>

<svelte:head>
	<title>Knowledge • Workspace</title>
</svelte:head>

<div class="p-4 max-w-6xl mx-auto w-full">
	<div class="flex items-center justify-between mb-3">
		<h1 class="text-xl font-semibold">
			{$i18n.t('Knowledge')}
			<span class="ml-2 text-xs font-normal text-neutral-500">
				{$i18n.t('Admin Lab Resource Editor')}
			</span>
		</h1>
	</div>

	{#if loading}
		<div class="text-sm text-neutral-500">{$i18n.t('Loading')}…</div>
	{:else}
		<!-- Top: Course + Lab selector + Student view button -->
		<div
			class="mb-4 grid gap-3 md:grid-cols-[minmax(0,2fr)_minmax(0,2fr)_auto] items-end"
		>
			<!-- Course selector -->
			<div>
				<label class="block text-xs mb-1 text-neutral-500">
					{$i18n.t('Course')}
				</label>
				<select
					class="w-full border rounded-md px-2 py-1 text-sm bg-transparent"
					on:change={handleCourseChange}
					bind:value={selectedCourseId}
				>
					<option value="">{ $i18n.t('Select course…') }</option>
					{#each courses as course}
						<option value={course.id}>
							{course.code ?? course.short_name ?? course.name}
						</option>
					{/each}
				</select>
			</div>

			<!-- Lab selector -->
			<div>
				<label class="block text-xs mb-1 text-neutral-500">
					{$i18n.t('Lab')}
				</label>
				<select
					class="w-full border rounded-md px-2 py-1 text-sm bg-transparent"
					on:change={handleLabChange}
					bind:value={selectedLabId}
					disabled={!selectedCourseId || labsForCourse.length === 0}
				>
					<option value="">{ $i18n.t('Select lab…') }</option>
					{#each labsForCourse as labItem}
						<option value={labItem.id}>
							{labItem.name}
						</option>
					{/each}
				</select>
			</div>

			<!-- Open Lab Resources (student view) -->
			<div class="flex justify-start md:justify-end">
				<button
					class="text-xs px-3 py-1 rounded-md border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800 disabled:opacity-50"
					on:click={openStudentView}
					disabled={!selectedLabId}
				>
					{$i18n.t('Open Lab Resources View')}
				</button>
			</div>
		</div>

		<!-- Bottom: Knowledge editor -->
		{#if selectedKnowledgeId}
			<div class="border rounded-lg overflow-hidden">
				{#key selectedKnowledgeId}
					<KnowledgeBase knowledgeId={selectedKnowledgeId} />
				{/key}
			</div>
		{:else if selectedLab}
			<div class="text-sm text-amber-600">
				{$i18n.t('This lab does not have a knowledge collection linked yet.')}
			</div>
		{:else}
			<div class="text-sm text-neutral-500">
				{$i18n.t('Select a course and lab to edit its resources.')}
			</div>
		{/if}
	{/if}
</div>
