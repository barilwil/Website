<script lang="ts">
	import { goto } from '$app/navigation';
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
		code: string;
		name: string;
		description?: string;
		enabled?: boolean;
		labs: Lab[];
	};

	let courses: Course[] = [];

	let selectedCourseId: string | null = null;
	let selectedLabId: string | null = null;

	let loadingCourses = true;
	let loadingLabs = false;

	// derived values
	$: selectedCourse = courses.find((c) => c.id === selectedCourseId) ?? null;
	$: labsForCourse = selectedCourse ? selectedCourse.labs : [];

	onMount(async () => {
		try {
			const res = (await getCourses(localStorage.token)) as any[];

			// map + keep only enabled courses
			courses = res
				.map((c) => ({
					id: c.id,
					code: c.code,
					name: c.name,
					description: c.description,
					enabled: c.enabled ?? true,
					labs: []
				}))
				.filter((c) => c.enabled);
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			loadingCourses = false;
		}
	});

	async function handleSelectCourse(courseId: string) {
		if (selectedCourseId === courseId) return;

		selectedCourseId = courseId;
		selectedLabId = null;

		const course = courses.find((c) => c.id === courseId);
		if (!course) return;

		// Only load labs once per course
		if (course.labs.length === 0) {
			await loadLabsForCourse(course);
		}
	}

	async function loadLabsForCourse(course: Course) {
		loadingLabs = true;
		try {
			const res = (await getLabsForCourse(localStorage.token, course.id)) as any[];

			const labs: Lab[] = res.map((l) => ({
				id: l.id,
				name: l.name,
				description: l.description,
				enabled: l.enabled ?? true
			}));

			// Only keep enabled labs for students
			const enabledLabs = labs.filter((l) => l.enabled);

			courses = courses.map((c) =>
				c.id === course.id ? { ...c, labs: enabledLabs } : c
			);
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			loadingLabs = false;
		}
	}

	function handleSelectLab(labId: string) {
		selectedLabId = labId;
	}

	function handleStart() {
		if (!selectedCourseId || !selectedLabId) return;

		// Go into the lab session route
		goto(
			`/labs/${encodeURIComponent(selectedCourseId)}/${encodeURIComponent(
				selectedLabId
			)}`
		);
	}

	function goBack() {
		goto('/');
	}
</script>

<div class="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-10">
	<div
		class="w-full max-w-3xl rounded-3xl bg-white dark:bg-neutral-900 shadow-xl border border-neutral-200 dark:border-neutral-800 px-6 py-5 md:px-8 md:py-6 space-y-4"
	>
		<header class="flex items-center justify-between gap-3">
			<div>
				<h1 class="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
					Course Labs
				</h1>
				<p class="text-sm text-neutral-500">
					Select your course, then your lab. Each lab has its own chat and resources.
				</p>
			</div>

			<button
				type="button"
				class="text-xs text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200 underline underline-offset-4"
				on:click={goBack}
			>
				Back
			</button>
		</header>

		<div class="space-y-4 md:space-y-5">
			<!-- Step 1: Course selection -->
			<section class="rounded-2xl border border-neutral-200 dark:border-neutral-800 px-4 py-3">
				<div class="flex items-center justify-between gap-2">
					<div>
						<div class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
							Step 1 · Choose your course
						</div>
						<p class="text-xs text-neutral-500 mt-1">
							Pick the course you’re currently in.
						</p>
					</div>
				</div>

				{#if loadingCourses}
					<p class="mt-3 text-xs text-neutral-500">Loading courses…</p>
				{:else if courses.length === 0}
					<p class="mt-3 text-xs text-neutral-500">
						No courses are available yet. An instructor needs to create and enable them
						in the admin panel.
					</p>
				{:else}
					<div class="mt-3 space-y-2">
						{#each courses as course}
							<button
								type="button"
								class={`w-full rounded-2xl px-4 py-3 text-left transition border ${
									selectedCourseId === course.id
										? 'bg-neutral-900 text-neutral-50 border-neutral-900'
										: 'bg-neutral-50 dark:bg-neutral-900/40 text-neutral-900 dark:text-neutral-50 border-neutral-200 dark:border-neutral-700 hover:border-neutral-400 dark:hover:border-neutral-500'
								}`}
								on:click={() => handleSelectCourse(course.id)}
							>
								<div class="flex flex-col gap-1">
									<div class="flex items-baseline justify-between gap-2">
										<div class="text-sm font-semibold">
											{course.code}
											<span class="ml-1 text-xs font-normal text-neutral-300 dark:text-neutral-500">
												· {course.name}
											</span>
										</div>
									</div>

									{#if course.description}
										<p
											class={`text-xs ${
												selectedCourseId === course.id
													? 'text-neutral-200'
													: 'text-neutral-500'
											} line-clamp-2`}
										>
											{course.description}
										</p>
									{/if}
								</div>
							</button>
						{/each}
					</div>
				{/if}
			</section>

			<!-- Step 2: Lab selection -->
			<section class="rounded-2xl border border-neutral-200 dark:border-neutral-800 px-4 py-3">
				<div class="flex items-center justify-between gap-2">
					<div>
						<div class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
							Step 2 · Choose your lab
						</div>
						<p class="text-xs text-neutral-500 mt-1">
							Select the specific lab session for tailored resources.
						</p>
					</div>
				</div>

				{#if !selectedCourse}
					<p class="mt-3 text-xs text-neutral-500">
						Choose a course above to see its labs.
					</p>
				{:else if loadingLabs}
					<p class="mt-3 text-xs text-neutral-500">Loading labs…</p>
				{:else if labsForCourse.length === 0}
					<p class="mt-3 text-xs text-neutral-500">
						No labs have been created or enabled yet for
						<span class="font-medium">{selectedCourse.code}</span>.
					</p>
				{:else}
					<div class="mt-3 space-y-2">
						{#each labsForCourse as lab}
							<button
								type="button"
								class={`w-full rounded-2xl px-4 py-3 text-left transition border ${
									selectedLabId === lab.id
										? 'bg-neutral-900 text-neutral-50 border-neutral-900'
										: 'bg-neutral-50 dark:bg-neutral-900/40 text-neutral-900 dark:text-neutral-50 border-neutral-200 dark:border-neutral-700 hover:border-neutral-400 dark:hover:border-neutral-500'
								}`}
								on:click={() => handleSelectLab(lab.id)}
							>
								<div class="flex flex-col gap-1">
									<div class="flex items-baseline justify-between gap-2">
										<div class="text-sm font-semibold">
											{lab.name}
										</div>
									</div>

									{#if lab.description}
										<p
											class={`text-xs ${
												selectedLabId === lab.id
													? 'text-neutral-200'
													: 'text-neutral-500'
											} line-clamp-2`}
										>
											{lab.description}
										</p>
									{/if}
								</div>
							</button>
						{/each}
					</div>

					<div class="mt-4 flex justify-end">
						<button
							type="button"
							class="rounded-full px-6 py-2 text-sm font-medium text-white bg-neutral-900 hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed transition"
							on:click={handleStart}
							disabled={!selectedLabId}
						>
							Start Assistant
						</button>
					</div>
				{/if}
			</section>
		</div>
	</div>
</div>
