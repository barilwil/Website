<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getFiles, uploadFile, getFileContentById, deleteFileById } from '$lib/apis/files';
	import { formatFileSize } from '$lib/utils';

	const i18n = getContext('i18n');

	let files: any[] = [];
	let loading = true;
	let uploading = false;
	let deletingId: string | null = null;

	// Preview overlay state (match lab-resources style)
	let previewFile: any = null;
	let previewUrl: string | null = null;
	let previewText: string | null = null;
	let previewMode: 'pdf' | 'image' | 'text' | 'other' | null = null;
	let previewLoading = false;
	let previewError: string | null = null;

	onMount(async () => {
		await refreshFiles();
	});

	async function refreshFiles() {
		loading = true;
		try {
			const res = await getFiles(localStorage.token);
			// API returns either an array or { items: [...] }
			files = Array.isArray(res) ? res : (res?.items ?? []);
		} catch (e) {
			console.error(e);
			toast.error(`${e}`);
		} finally {
			loading = false;
		}
	}

	function getFileName(file: any) {
		return file?.filename || file?.name || 'untitled';
	}

	function getFileExtension(file: any): string {
		const name = getFileName(file).toLowerCase();
		const dot = name.lastIndexOf('.');
		if (dot === -1) return '';
		return name.slice(dot + 1);
	}

	function guessPreviewMode(file: any): 'pdf' | 'image' | 'text' | 'other' {
		const ext = getFileExtension(file);

		if (ext === 'pdf') return 'pdf';
		if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext)) return 'image';
		if (
			[
				'txt',
				'md',
				'sp',
				'cir',
				'net',
				'spice',
				'py',
				'cpp',
				'c',
				'h',
				'json',
				'csv',
				'log'
			].includes(ext)
		) {
			return 'text';
		}
		return 'other';
	}

	async function getBlobForFile(file: any): Promise<Blob> {
		const res: any = await getFileContentById(file.id);

		// getFileContentById may return a Response or a Blob
		if (res?.blob && typeof res.blob === 'function') {
			return await res.blob();
		}
		return res as Blob;
	}

	async function onUploadChange(e: Event) {
		const input = e.target as HTMLInputElement;
		if (!input.files || input.files.length === 0) return;

		uploading = true;
		try {
			for (const file of Array.from(input.files)) {
				await uploadFile(localStorage.token, file, null);
			}
			await refreshFiles();
			toast.success($i18n.t('Upload complete'));
		} catch (err) {
			console.error(err);
			toast.error(`${err}`);
		} finally {
			uploading = false;
			(e.target as HTMLInputElement).value = '';
		}
	}

	async function openPreview(file: any) {
		previewFile = file;
		previewUrl = null;
		previewText = null;
		previewMode = null;
		previewError = null;
		previewLoading = true;

		try {
			const mode = guessPreviewMode(file);
			previewMode = mode;

			const blob = await getBlobForFile(file);

			if (mode === 'text') {
				previewText = await blob.text();
			} else {
				previewUrl = URL.createObjectURL(blob);
			}
		} catch (e) {
			console.error(e);
			previewError = `${e}`;
			toast.error(`${e}`);
		} finally {
			previewLoading = false;
		}
	}

	function closePreview() {
		if (previewUrl) {
			URL.revokeObjectURL(previewUrl);
		}
		previewFile = null;
		previewUrl = null;
		previewText = null;
		previewMode = null;
		previewError = null;
	}

	async function download(file: any) {
		try {
			const blob = await getBlobForFile(file);
			const a = document.createElement('a');
			a.href = URL.createObjectURL(blob);
			a.download = getFileName(file);
			a.click();
			URL.revokeObjectURL(a.href);
		} catch (e) {
			console.error(e);
			toast.error(`${e}`);
		}
	}

	async function removeFile(f: any) {
		if (!f?.id) return;

		const confirmed = window.confirm($i18n.t('Are you sure you want to delete this file?'));
		if (!confirmed) return;

		deletingId = f.id;
		try {
			await deleteFileById(localStorage.token, f.id);

			files = files.filter((file) => file.id !== f.id);
			if (previewFile?.id === f.id) {
				closePreview();
			}

			toast.success($i18n.t('File deleted'));
		} catch (err) {
			console.error(err);
			toast.error($i18n.t('Failed to delete file'));
		} finally {
			deletingId = null;
		}
	}
</script>

<svelte:head>
	<title>My Uploads • Workspace</title>
</svelte:head>

<div class="min-h-[calc(100vh-4rem)] flex-1 px-4 py-8 bg-white dark:bg-neutral-950">
	<div class="max-w-6xl mx-auto relative">
		<!-- Preview overlay (same vibe as lab-resources) -->
		{#if previewFile}
			<div
				class="fixed inset-0 z-60 flex items-center justify-center px-4 py-8 bg-black/50 backdrop-blur-sm"
			>
			<div
					class="relative w-full max-w-5xl max-h-[90vh] rounded-2xl bg-white dark:bg-neutral-950 shadow-2xl flex flex-col overflow-hidden"
				>
					<header
						class="flex items-start justify-between gap-3 px-4 py-3 border-b border-neutral-200 dark:border-neutral-800"
					>
						<div class="min-w-0">
							<div class="text-sm font-semibold text-neutral-900 dark:text-neutral-50 line-clamp-2">
								{getFileName(previewFile)}
							</div>
							<p class="mt-0.5 text-[11px] text-neutral-500 dark:text-neutral-400">
								{formatFileSize(previewFile.size ?? previewFile.meta?.size ?? 0)}
								{#if getFileExtension(previewFile)}
									&nbsp;· {getFileExtension(previewFile).toUpperCase()}
								{/if}
							</p>
						</div>

						<div class="flex items-center gap-2">
							<button
								type="button"
								class="rounded-full px-3 py-1 text-[11px] font-medium border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800"
								on:click={() => previewFile && download(previewFile)}
							>
								{$i18n.t('Download')}
							</button>
							<button
								type="button"
								class="h-8 w-8 rounded-full flex items-center justify-center border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-500 dark:text-neutral-400"
								on:click={closePreview}
							>
								<span class="sr-only">{$i18n.t('Close')}</span>
								×
							</button>
						</div>
					</header>

					<div class="flex-1 overflow-auto bg-neutral-50 dark:bg-neutral-900">
						{#if previewLoading}
							<div class="flex items-center justify-center h-64 text-sm text-neutral-500 dark:text-neutral-400">
								{$i18n.t('Loading preview…')}
							</div>
						{:else if previewError}
							<div class="p-4 text-sm text-red-500">
								{$i18n.t('Unable to load preview.')} {previewError}
							</div>
						{:else if previewMode === 'pdf' && previewUrl}
							<iframe
								src={previewUrl}
								class="w-full h-[70vh] border-0"
								title={getFileName(previewFile)}
							/>
						{:else if previewMode === 'image' && previewUrl}
							<div class="flex items-center justify-center p-4">
								<img
									src={previewUrl}
									alt={getFileName(previewFile)}
									class="max-h-[70vh] max-w-full object-contain rounded-xl"
								/>
							</div>
						{:else if previewMode === 'text' && previewText !== null}
							<pre
								class="p-4 text-xs leading-relaxed font-mono whitespace-pre-wrap break-words bg-neutral-900 text-neutral-100 max-h-[70vh] overflow-auto"
							>
{previewText}
							</pre>
						{:else}
							<div class="p-4 text-sm text-neutral-500 dark:text-neutral-400">
								{$i18n.t("This file type doesn't have an inline preview.")}
								<br />
								{$i18n.t('Use the Download button to open it locally.')}
							</div>
						{/if}
					</div>
				</div>
			</div>
		{/if}

		<!-- Page header -->
		<div class="flex items-center justify-between gap-3 mb-4">
			<div>
				<h1 class="text-xl font-semibold text-neutral-900 dark:text-neutral-50">
					{$i18n.t('My Uploads')}
				</h1>
				<p class="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
					{$i18n.t('Files you upload here are available in your Workspace across chats.')}
				</p>
			</div>

			<label
				class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-neutral-100 dark:bg-neutral-800 cursor-pointer text-sm font-medium"
			>
				<span>
					{uploading ? $i18n.t('Uploading…') : $i18n.t('Upload files')}
				</span>
				<input
					type="file"
					class="hidden"
					multiple
					on:change={onUploadChange}
					disabled={uploading}
				/>
			</label>
		</div>

		{#if loading}
			<div class="mt-4 text-sm text-neutral-500 dark:text-neutral-400">
				{$i18n.t('Loading')}…
			</div>
		{:else if files.length === 0}
			<div
				class="mt-4 rounded-2xl border border-dashed border-neutral-300 dark:border-neutral-700 px-6 py-8 text-sm text-neutral-500 dark:text-neutral-400 bg-white dark:bg-neutral-900/60 text-center"
			>
				{$i18n.t("You haven’t uploaded any files yet.")}<br />
				<span class="text-xs">
					{$i18n.t('Use “Upload files” to add PDFs, images, code, or SPICE files.')}
				</span>
			</div>
		{:else}
			<div class="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
				{#each files as f}
					<article
						class="group rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900/70 px-3 py-3 flex flex-col justify-between shadow-sm"
					>
						<div class="min-w-0">
							<button
								type="button"
								class="text-sm font-medium text-left line-clamp-2 text-neutral-900 dark:text-neutral-50 group-hover:text-blue-600 dark:group-hover:text-blue-300"
								on:click={() => openPreview(f)}
							>
								{getFileName(f)}
							</button>
							<p class="mt-1 text-[11px] text-neutral-500 dark:text-neutral-400">
								{formatFileSize(f.size ?? f.meta?.size ?? 0)}
								{#if getFileExtension(f)}
									&nbsp;· {getFileExtension(f).toUpperCase()}
								{/if}
							</p>
						</div>

						<div class="mt-3 flex items-center justify-between gap-2 text-[11px]">
							<div class="flex gap-2">
								<button
									type="button"
									class="px-3 py-1 rounded-full border border-neutral-200 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800"
									on:click={() => openPreview(f)}
								>
									{$i18n.t('Preview')}
								</button>
								<button
									type="button"
									class="px-3 py-1 rounded-full border border-neutral-200 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800"
									on:click={() => download(f)}
								>
									{$i18n.t('Download')}
								</button>
							</div>

							<button
								type="button"
								class="px-3 py-1 rounded-full border border-red-300 text-red-600 hover:bg-red-50 dark:border-red-700 dark:text-red-400 dark:hover:bg-red-950 disabled:opacity-60"
								on:click={() => removeFile(f)}
								disabled={deletingId === f.id}
							>
								{#if deletingId === f.id}
									{$i18n.t('Deleting…')}
								{:else}
									{$i18n.t('Delete')}
								{/if}
							</button>
						</div>
					</article>
				{/each}
			</div>
		{/if}
	</div>
</div>
