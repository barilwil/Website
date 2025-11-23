<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	onMount(() => {
		if ($page.url.searchParams.get('error')) {
			toast.error($page.url.searchParams.get('error') || 'An unknown error occurred.');
		}
	});

	const goToGeneralAssistant = () => {
		goto('/assistant');
	};

	const goToClassMode = () => {
		goto('/labs');
	};
</script>

<!-- IMPORTANT: use h-full, not h-screen; and no m-auto -->
<div class="w-full h-full flex items-center justify-center bg-neutral-50 dark:bg-neutral-900">
	<div
		class="max-w-3xl w-full mx-4 px-6 py-10 rounded-3xl shadow-lg
           bg-white dark:bg-neutral-800"
	>
		<h1 class="text-2xl font-semibold mb-2 text-center">
			How do you want to use the assistant?
		</h1>
		<p class="text-sm text-center text-neutral-500 mb-8">
			Choose “Course Labs” for lab-specific help, or “General Assistant” for homework and
			concept questions.
		</p>

		<div class="grid gap-6 md:grid-cols-2">
			<button
				type="button"
				class="flex flex-col items-start gap-2 rounded-2xl border border-neutral-200
               dark:border-neutral-700 px-5 py-4 hover:border-blue-500 hover:shadow
               transition w-full"
				on:click={goToClassMode}
			>
				<span class="text-sm font-semibold">Course Labs</span>
				<span class="text-xs text-neutral-500">
          Pick your class and lab. The assistant loads that lab’s manual and resources.
        </span>
			</button>

			<button
				type="button"
				class="flex flex-col items-start gap-2 rounded-2xl border border-neutral-200
               dark:border-neutral-700 px-5 py-4 hover:border-blue-500 hover:shadow
               transition w-full"
				on:click={goToGeneralAssistant}
			>
				<span class="text-sm font-semibold">General Assistant</span>
				<span class="text-xs text-neutral-500">
          Open a blank chat for theory review, homework help, or general questions.
        </span>
			</button>
		</div>
	</div>
</div>
