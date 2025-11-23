<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Chat from '$lib/components/chat/Chat.svelte';
	import LabResources from '$lib/components/labs/LabResources.svelte';
	import { getLabById } from '$lib/apis/labs';

	let lab: any = null;
	let loadingLab = true;

	$: classId = $page.params.classId;
	$: labId = $page.params.labId;

	onMount(async () => {
		try {
			lab = await getLabById(localStorage.token, labId);
		} catch (e) {
			console.error(e);
			toast.error(`${e}`);
		} finally {
			loadingLab = false;
		}
	});
</script>

<!-- Same navbar / layout as General Assistant, Chat owns the top bar -->
<div class="flex h-[calc(100vh-4rem)] md:h-[calc(100vh-3.5rem)]">
	<!-- Main chat area -->
	<div class="flex-1 min-w-0">
		<Chat />
	</div>

	<!-- Lab materials panel -->
	{#if !loadingLab && lab?.knowledge_id}
		<div class="hidden lg:flex">
			<LabResources
				labName={`${lab?.name ?? ''}`}
				description={lab?.description}
				knowledgeId={lab.knowledge_id}
			/>
		</div>
	{/if}
</div>
