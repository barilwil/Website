<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getKnowledgeById } from '$lib/apis/knowledge';
	import Files from '$lib/components/workspace/Knowledge/KnowledgeBase/Files.svelte';

	const i18n = getContext('i18n');

	export let labName: string;
	export let description: string | undefined = undefined;
	export let knowledgeId: string | null = null;

	let loading = true;
	let knowledge: any = null;
	let files: any[] = [];
	let selectedFileId: string | null = null;

	onMount(async () => {
		if (!knowledgeId) {
			loading = false;
			return;
		}

		try {
			const res = await getKnowledgeById(localStorage.token, knowledgeId);
			knowledge = res;
			files = res?.files ?? [];
		} catch (e) {
			console.error(e);
			toast.error(`${e}`);
		} finally {
			loading = false;
		}
	});
</script>

<aside
	class="h-full w-80 xl:w-96 border-l border-neutral-200 dark:border-neutral-800 bg-neutral-50/80 dark:bg-neutral-900/80 backdrop-blur-sm flex flex-col"
>
	<!-- Header -->
	<div class="px-4 py-3 border-b border-neutral-200 dark:border-neutral-800">
		<div class="text-[11px] font-semibold uppercase tracking-wide text-neutral-500">
			Lab Materials
		</div>
		<div
			class="mt-1 text-xs text-neutral-900 dark:text-neutral-100 font-medium truncate"
			title={labName}
		>
			{labName}
		</div>
		{#if description}
			<div class="mt-0.5 text-[11px] text-neutral-500 line-clamp-2" title={description}>
				{description}
			</div>
		{/if}
	</div>

	<!-- Body -->
	{#if !knowledgeId}
		<div class="p-4 text-xs text-neutral-500">
			No collection is linked to this lab yet.
		</div>
	{:else if loading}
		<div class="p-4 text-xs text-neutral-500">
			Loading materials…
		</div>
	{:else if !files.length}
		<div class="p-4 text-xs text-neutral-500">
			No files have been added to this lab’s collection yet.
		</div>
	{:else}
		<div class="flex-1 overflow-hidden flex flex-col">
			<div class="px-4 pt-3 pb-2 text-[11px] uppercase tracking-wide text-neutral-500">
				Resources ({files.length})
			</div>

			<div class="flex-1 overflow-y-auto text-xs">
				<Files
					small
					files={files}
					{selectedFileId}
					on:click={(e) => {
						selectedFileId = selectedFileId === e.detail ? null : e.detail;
					}}
				/>
			</div>
		</div>
	{/if}

	<!-- Footer hint -->
	<div
		class="px-4 py-3 border-t border-neutral-200 dark:border-neutral-800 text-[11px] text-neutral-500"
	>
		Manage files under <span class="font-medium">Workspace → Knowledge</span>.
	</div>
</aside>
