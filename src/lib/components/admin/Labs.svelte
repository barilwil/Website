<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';

	import {
		getCourses,
		getLabsForCourse,
		createCourse,
		updateCourse
	} from '$lib/apis/courses';
	import { createLab, updateLab } from '$lib/apis/labs';

	const i18n = getContext('i18n');

	type Lab = {
		id: string;
		name: string;
		description?: string;
		enabled: boolean;
	};

	type Course = {
		id: string;
		code: string;
		name: string;
		description?: string;
		enabled: boolean;
		labs: Lab[];
	};

	let courses: Course[] = [];
	let selectedCourseId: string | null = null;
	let selectedCourse: Course | null = null;

	let loading = true;
	let saving = false;

	// New course form
	let newCourseCode = '';
	let newCourseName = '';
	let newCourseDescription = '';

	// New lab form
	let newLabName = '';
	let newLabDescription = '';

	$: selectedCourse =
		courses.find((c) => c.id === selectedCourseId) ?? (courses.length ? courses[0] : null);

	onMount(async () => {
		// double-check admin
		if ($user?.role !== 'admin') {
			await goto('/assistant');
			return;
		}

		await loadCourses();
	});

	async function loadCourses() {
		loading = true;

		try {
			const rawCourses = (await getCourses(localStorage.token)) as any[];

			const loaded: Course[] = [];
			for (const c of rawCourses) {
				const labsRaw = (await getLabsForCourse(localStorage.token, c.id)) as any[];

				loaded.push({
					id: c.id,
					code: c.code,
					name: c.name,
					description: c.description,
					enabled: c.enabled ?? true,
					labs: labsRaw.map((l) => ({
						id: l.id,
						name: l.name,
						description: l.description,
						enabled: l.enabled ?? true
					}))
				});
			}

			courses = loaded;
			if (!selectedCourseId && courses.length) {
				selectedCourseId = courses[0].id;
			}
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			loading = false;
		}
	}

	function selectCourse(id: string) {
		selectedCourseId = id;
	}

	async function handleCreateCourse() {
		if (!newCourseCode.trim() || !newCourseName.trim()) {
			toast.error('Course code and name are required');
			return;
		}

		saving = true;
		try {
			const created = await createCourse(localStorage.token, {
				code: newCourseCode.trim(),
				name: newCourseName.trim(),
				description: newCourseDescription.trim() || undefined,
				enabled: true
			});

			toast.success('Course created');

			newCourseCode = '';
			newCourseName = '';
			newCourseDescription = '';

			await loadCourses();
			selectedCourseId = created.id;
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			saving = false;
		}
	}

	async function toggleCourseEnabled(course: Course) {
		saving = true;
		try {
			const updated = await updateCourse(localStorage.token, course.id, {
				enabled: !course.enabled
			});

			courses = courses.map((c) =>
				c.id === course.id ? { ...c, enabled: updated.enabled ?? !course.enabled } : c
			);
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			saving = false;
		}
	}

	async function handleCreateLab() {
		if (!selectedCourse) {
			toast.error('Select a course first');
			return;
		}
		if (!newLabName.trim()) {
			toast.error('Lab name is required');
			return;
		}

		saving = true;
		try {
			await createLab(localStorage.token, {
				course_id: selectedCourse.id,
				name: newLabName.trim(),
				description: newLabDescription.trim() || undefined,
				enabled: true
			});

			toast.success('Lab created');

			newLabName = '';
			newLabDescription = '';

			await loadCourses();
			selectedCourseId = selectedCourse.id;
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			saving = false;
		}
	}

	async function toggleLabEnabled(course: Course, lab: Lab) {
		saving = true;
		try {
			const updated = await updateLab(localStorage.token, lab.id, {
				enabled: !lab.enabled
			});

			courses = courses.map((c) =>
				c.id === course.id
					? {
						...c,
						labs: c.labs.map((l) =>
							l.id === lab.id ? { ...l, enabled: updated.enabled ?? !lab.enabled } : l
						)
					}
					: c
			);
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			saving = false;
		}
	}
</script>

<main class="p-4 md:p-6 max-w-5xl mx-auto space-y-4">
	<header class="flex items-center justify-between">
		<div>
			<h1 class="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
				{$i18n.t('Labs')}
			</h1>
			<p class="text-sm text-neutral-500">
				Manage courses and labs. Enabling a lab will make it visible to students on the labs page.
			</p>
		</div>

		{#if saving}
			<div class="text-xs text-neutral-500">Saving…</div>
		{/if}
	</header>

	{#if loading}
		<div class="text-sm text-neutral-500">Loading courses…</div>
	{:else}
		{#if courses.length === 0}
			<div class="rounded-xl border border-dashed border-neutral-300 dark:border-neutral-700 p-4 text-sm text-neutral-500">
				No courses yet. Create your first course below.
			</div>
		{/if}

		<div class="grid grid-cols-1 md:grid-cols-[260px,minmax(0,1fr)] gap-4">
			<!-- Courses list + new course form -->
			<section class="space-y-4">
				<div class="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-3">
					<div class="flex items-center justify-between mb-2">
						<h2 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
							Courses
						</h2>
					</div>

					<div class="space-y-1 max-h-64 overflow-y-auto">
						{#each courses as course}
							<button
								type="button"
								class={`w-full flex items-center justify-between rounded-xl px-3 py-2 text-left text-sm border transition ${
									selectedCourse?.id === course.id
										? 'border-neutral-900 dark:border-neutral-50 bg-neutral-900/5 dark:bg-neutral-50/5'
										: 'border-neutral-200 dark:border-neutral-700 hover:border-neutral-400 dark:hover:border-neutral-500'
								}`}
								on:click={() => selectCourse(course.id)}
							>
								<div>
									<div class="font-medium">
										{course.code}
										<span class="ml-1 text-xs text-neutral-500">{course.name}</span>
									</div>
									{#if course.description}
										<p class="text-xs text-neutral-500 line-clamp-2 mt-0.5">
											{course.description}
										</p>
									{/if}
								</div>

								<label class="flex items-center gap-1 text-[11px] text-neutral-500">
									<input
										type="checkbox"
										checked={course.enabled}
										on:change={() => toggleCourseEnabled(course)}
									/>
									<span>Enabled</span>
								</label>
							</button>
						{/each}
					</div>
				</div>

				<!-- New course form -->
				<div class="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-3 space-y-2">
					<h3 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
						New course
					</h3>

					<div class="space-y-2">
						<input
							class="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-2 py-1 text-xs"
							placeholder="Course code (e.g. ECEN 403)"
							bind:value={newCourseCode}
						/>
						<input
							class="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-2 py-1 text-xs"
							placeholder="Course name"
							bind:value={newCourseName}
						/>
						<textarea
							class="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-2 py-1 text-xs resize-none"
							rows="2"
							placeholder="Optional description"
							bind:value={newCourseDescription}
						/>
					</div>

					<button
						type="button"
						class="mt-1 inline-flex items-center justify-center rounded-full px-4 py-1.5 text-xs font-medium text-white bg-neutral-900 hover:bg-neutral-800 disabled:opacity-60"
						on:click={handleCreateCourse}
						disabled={saving}
					>
						Add course
					</button>
				</div>
			</section>

			<!-- Labs for selected course -->
			<section class="space-y-4">
				{#if !selectedCourse}
					<div class="rounded-2xl border border-dashed border-neutral-300 dark:border-neutral-700 p-4 text-sm text-neutral-500">
						Select a course on the left to manage its labs.
					</div>
				{:else}
					<div class="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-3">
						<div class="flex items-center justify-between mb-2">
							<div>
								<h2 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
									Labs for {selectedCourse.code}
								</h2>
								<p class="text-[11px] text-neutral-500">
									Each lab has its own chat channel and knowledge base.
								</p>
							</div>
						</div>

						{#if selectedCourse.labs.length === 0}
							<p class="text-xs text-neutral-500">
								No labs yet for this course.
							</p>
						{:else}
							<div class="space-y-1 max-h-64 overflow-y-auto">
								{#each selectedCourse.labs as lab}
									<div
										class="flex items-center justify-between rounded-xl border border-neutral-200 dark:border-neutral-700 px-3 py-2 text-sm"
									>
										<div>
											<div class="font-medium">{lab.name}</div>
											{#if lab.description}
												<p class="text-xs text-neutral-500 line-clamp-2 mt-0.5">
													{lab.description}
												</p>
											{/if}
										</div>

										<label class="flex items-center gap-1 text-[11px] text-neutral-500">
											<input
												type="checkbox"
												checked={lab.enabled}
												on:change={() => toggleLabEnabled(selectedCourse, lab)}
											/>
											<span>Enabled</span>
										</label>
									</div>
								{/each}
							</div>
						{/if}
					</div>

					<!-- New lab form -->
					<div class="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-3 space-y-2">
						<h3 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
							New lab for {selectedCourse.code}
						</h3>

						<div class="space-y-2">
							<input
								class="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-2 py-1 text-xs"
								placeholder="Lab name (e.g. Lab 1 – Op-amp basics)"
								bind:value={newLabName}
							/>
							<textarea
								class="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-2 py-1 text-xs resize-none"
								rows="2"
								placeholder="Optional description"
								bind:value={newLabDescription}
							/>
						</div>

						<button
							type="button"
							class="mt-1 inline-flex items-center justify-center rounded-full px-4 py-1.5 text-xs font-medium text-white bg-neutral-900 hover:bg-neutral-800 disabled:opacity-60"
							on:click={handleCreateLab}
							disabled={saving}
						>
							Add lab
						</button>
					</div>
				{/if}
			</section>
		</div>
	{/if}
</main>
