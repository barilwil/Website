<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Chat from '$lib/components/chat/Chat.svelte';
	import { getLabById } from '$lib/apis/labs';
	import { chatBasePath, chatContext } from '$lib/stores';

	let lab: any = null;

	$: classId = $page.params.classId;
	$: labId = $page.params.labId;

	onMount(async () => {
		// remember that this page is the current chat context
		chatBasePath.set($page.url.pathname);
		chatContext.set({
			context_type: 'lab',
			course_id: classId,
			lab_id: labId
		});

		try {
			lab = await getLabById(localStorage.token, labId);
		} catch (e) {
			console.error(e);
			toast.error(`${e}`);
		}
	});
</script>

<!-- Exactly like /assistant, but with a lab-specific title -->
<Chat labTitle={`${classId?.toUpperCase?.() ?? classId} • ${lab?.name ?? ''}`} />