<script lang="ts">
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { onMount } from 'svelte';

	onMount(() => {
		// If we somehow don't have a user yet, fall back to assistant
		if (!$user) {
			goto('/assistant');
			return;
		}

		//  Admins:
		// Workspace is their control center, so ALWAYS send them to the Knowledge editor,
		// regardless of any workspace permission flags.
		if ($user.role === 'admin') {
			goto('/workspace/knowledge');
			return;
		}

		//  Non-admins (students, TAs, etc.)
		// Choose the first "advanced" workspace tab allowed by permissions,
		// but always fall back to My Uploads so Workspace actually opens.
		if ($user.permissions?.workspace?.models) {
			goto('/workspace/models');
		} else if ($user.permissions?.workspace?.tools) {
			goto('/workspace/tools');
		} else {
			// Safe fallback: every logged-in user can access My Uploads
			goto('/workspace/my-uploads');
		}
	});
</script>
