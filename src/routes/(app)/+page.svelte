<!--
Course dashboard page.
- Loads enabled/enrolled courses and their enabled labs from the backend.
- Shows one card per course with lab "tabs" to pick an active lab.
- Displays the selected lab’s description and routes to `/labs/<course>/<labId>` when opened.
- Includes a shortcut to the general assistant (`/assistant`).
-->

<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getCourses, getLabsForCourse } from '$lib/apis/courses';

	type Lab = {
		id: string;
		name: string;
		description?: string;
		enabled?: boolean;
	};

	type Course = {
		id: string;
		code?: string;
		name?: string;
		description?: string;
		enabled?: boolean;
		labs: Lab[];
	};

	let loadingCourses = true;
	let courses: Course[] = [];

	// Which lab is selected for each course (for the "tabs")
	let selectedLabs: Record<string, string | null> = {};

	onMount(async () => {
		const errorParam = $page.url.searchParams.get('error');
		if (errorParam) {
			toast.error(errorParam || 'An unknown error occurred.');
		}

		try {
			// 1) Load all courses the user can see
			const res = (await getCourses(localStorage.token)) as any[];

			const baseCourses: Course[] = (res ?? [])
				.map((c: any) => ({
					id: c.id,
					code: c.code,
					name: c.name,
					description: c.description,
					enabled: c.enabled ?? true,
					labs: []
				}))
				// Treat "enabled" courses as "enrolled / available"
				.filter((c) => c.enabled);

			const newSelectedLabs: Record<string, string | null> = {};

			// 2) For each course, load its labs
			await Promise.all(
				baseCourses.map(async (course) => {
					try {
						const labRes = (await getLabsForCourse(
							localStorage.token,
							course.id
						)) as any[];

						const labs: Lab[] = (labRes ?? []).map((l: any) => ({
							id: l.id,
							name: l.name,
							description: l.description,
							enabled: l.enabled ?? true
						}));

						course.labs = labs.filter((l) => l.enabled);

						// Default selected tab = first lab (or null if no labs)
						newSelectedLabs[course.id] =
							course.labs.length > 0 ? course.labs[0].id : null;
					} catch (e) {
						console.error(e);
						toast.error(`${e}`);
					}
				})
			);

			// Reassign so Svelte sees the updates
			courses = baseCourses;
			selectedLabs = newSelectedLabs;
		} catch (e) {
			console.error(e);
			toast.error(`${e}`);
		} finally {
			loadingCourses = false;
		}
	});

	function openLab(course: Course, lab: Lab) {
		const classCode = course.code ?? course.id;
		goto(`/labs/${encodeURIComponent(classCode)}/${encodeURIComponent(lab.id)}`);
	}

	function openGeneralAssistant() {
		goto('/assistant');
	}

	function selectLab(courseId: string, labId: string) {
		selectedLabs = { ...selectedLabs, [courseId]: labId };
	}
</script>

<div class="min-h-[calc(100vh-4rem)] flex-1 px-4 py-8">
	<div class="max-w-6xl mx-auto">
		<header class="flex items-center justify-between gap-3 mb-8">
			<div>
				<h1 class="text-2xl font-semibold text-neutral-900 dark:text-neutral-50">
					Course Dashboard
				</h1>
				<p class="text-sm text-neutral-500 dark:text-neutral-400">
					Choose a lab from your enrolled courses to open its assistant with the lab manual and
					resources.
				</p>
			</div>

			<button
				type="button"
				class="rounded-full px-4 py-2 text-xs sm:text-sm font-medium border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 hover:border-neutral-500 dark:hover:border-neutral-500 transition"
				on:click={openGeneralAssistant}
			>
				Open General Assistant
			</button>
		</header>

		{#if loadingCourses}
			<p class="text-sm text-neutral-500 dark:text-neutral-400">Loading your courses…</p>
		{:else if courses.length === 0}
			<div
				class="rounded-2xl border border-dashed border-neutral-300 dark:border-neutral-700 px-6 py-8 text-center text-sm text-neutral-500 dark:text-neutral-400"
			>
				No courses are available yet. Once an instructor adds you to a course, it will appear
				here with its labs.
			</div>
		{:else}
			<!-- One section per course, stacked like Canvas cards -->
			<div class="space-y-4">
				{#each courses as course}
					{@const labs = course.labs}
					{@const activeLab =
						labs.find((l) => l.id === selectedLabs[course.id]) ?? labs[0]}

					<section
						class="rounded-[24px] border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900/60 px-5 py-4"
					>
						<!-- Course title row (ECEN262 · Lasers  |  1 lab) -->
						<div class="flex items-center justify-between gap-3 mb-2">
							<div class="flex flex-col">
								<div
									class="text-sm sm:text-base font-semibold text-neutral-900 dark:text-neutral-50"
								>
									{course.code}
									{#if course.name}
										<span
											class="ml-1 text-sm font-normal text-neutral-400 dark:text-neutral-500"
										>
											· {course.name}
										</span>
									{/if}
								</div>

								{#if course.description}
									<p
										class="mt-1 text-xs text-neutral-500 dark:text-neutral-400 max-w-xl"
									>
										{course.description}
									</p>
								{/if}
							</div>

							{#if labs && labs.length > 0}
								<span
									class="text-[11px] rounded-full px-3 py-1 bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300"
								>
									{labs.length} lab{labs.length === 1 ? '' : 's'}
								</span>
							{/if}
						</div>

						{#if !labs || labs.length === 0}
							<p class="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
								This course doesn’t have any labs enabled yet.
							</p>
						{:else}
							<!-- Lab tabs directly under course title -->
							<div class="mt-1 flex flex-wrap gap-1.5" role="tablist" aria-label="Labs">
								{#each labs as lab}
									{@const isActive = activeLab && activeLab.id === lab.id}
									<button
										type="button"
										role="tab"
										aria-selected={isActive}
										class="px-3 py-1.5 text-xs sm:text-sm rounded-full border transition
											{isActive
												? 'bg-neutral-900 text-white border-neutral-900 dark:bg-white dark:text-neutral-900 dark:border-white'
												: 'bg-white text-neutral-700 border-neutral-200 hover:bg-neutral-50 hover:border-neutral-400 dark:bg-neutral-900 dark:text-neutral-200 dark:border-neutral-700 dark:hover:bg-neutral-800'}"
										on:click={() => selectLab(course.id, lab.id)}
									>
										{lab.name}
									</button>
								{/each}
							</div>

							<!-- Active lab description under tabs -->
							{#if activeLab}
								<div
									class="mt-3 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-900/80 px-3 py-3 text-xs sm:text-sm text-neutral-600 dark:text-neutral-200"
									role="tabpanel"
								>
									<div class="flex items-start justify-between gap-2">
										<div class="pr-2">
											<div
												class="text-sm font-semibold text-neutral-900 dark:text-neutral-50"
											>
												{activeLab.name}
											</div>

											{#if activeLab.description}
												<p class="mt-1 leading-relaxed">
													{activeLab.description}
												</p>
											{:else}
												<p class="mt-1 italic text-neutral-400 dark:text-neutral-500">
													No description provided for this lab yet.
												</p>
											{/if}
										</div>

										<button
											type="button"
											class="shrink-0 rounded-full px-3 py-1 text-[11px] font-medium bg-neutral-900 text-white hover:bg-neutral-800 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200 transition"
											on:click={() => openLab(course, activeLab)}
										>
											Open lab
										</button>
									</div>
								</div>
							{/if}
						{/if}
					</section>
				{/each}
			</div>
		{/if}
	</div>
</div>
