<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { page } from '$app/stores';

	import Chat from '$lib/components/chat/Chat.svelte';
	import { chatBasePath, chatContext } from '$lib/stores';

	onMount(() => {
		// remember that we’re in general chat
		chatBasePath.set('/assistant');
		chatContext.set({
			context_type: 'general',
			course_id: null,
			lab_id: null
		});

		if ($page.url.searchParams.get('error')) {
			toast.error($page.url.searchParams.get('error') || 'An unknown error occurred.');
		}
	});
</script>

<!-- This is your “General Assistant” chat -->
<Chat />
