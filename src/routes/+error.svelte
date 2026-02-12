<!---
Global error page.
Displays the HTTP status code and error message from SvelteKit's page store
for routing, load, or server-side failures.
-->
<script>
	import { page } from '$app/stores';
</script>

<div class=" bg-white dark:bg-gray-800 min-h-screen">
	<div class=" flex h-full">
		<div class="m-auto my-10 dark:text-gray-300 text-3xl font-semibold">
			{$page.status}: {$page.error?.message}
		</div>
	</div>
</div>
