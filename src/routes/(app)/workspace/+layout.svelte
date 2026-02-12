<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import {
		WEBUI_NAME,
		showSidebar,
		functions,
		user,
		mobile,
		models,
		prompts,
		knowledge,
		tools,
		chatContext
	} from '$lib/stores';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		// Redirect non-admins away from restricted Workspace areas
		if ($user?.role !== 'admin') {
			// Knowledge is admin-only now: always block students
			if ($page.url.pathname.includes('/workspace/knowledge')) {
				goto('/assistant');
			} else if (
				$page.url.pathname.includes('/workspace/models') &&
				!$user?.permissions?.workspace?.models
			) {
				goto('/assistant');
			} else if (
				$page.url.pathname.includes('/workspace/tools') &&
				!$user?.permissions?.workspace?.tools
			) {
				goto('/assistant');
			} else if ($page.url.pathname.includes('/workspace/functions') && $user?.role !== 'admin') {
				goto('/assistant');
			}
			// NOTE: Lab Resources & My Uploads are allowed for students; no redirects here.
		}

		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Workspace')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div
		class=" relative flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-260px)]'
			: ''} max-w-full"
	>
		<nav class="   px-2.5 pt-1.5 backdrop-blur-xl drag-region">
			<div class=" flex items-center gap-1">
				{#if $mobile}
					<div class="{$showSidebar ? 'md:hidden' : ''} self-center flex flex-none items-center">
						<Tooltip
							content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
							interactive={true}
						>
							<button
								id="sidebar-toggle-button"
								class=" cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition cursor-"
								on:click={() => {
									showSidebar.set(!$showSidebar);
								}}
							>
								<div class=" self-center p-1.5">
									<Sidebar />
								</div>
							</button>
						</Tooltip>
					</div>
				{/if}

				<div class="">
					<div
						class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent py-1 touch-auto pointer-events-auto"
					>
						{#if $user?.role === 'admin' || $user?.permissions?.workspace?.models}
							<a
								class="min-w-fit p-1.5 {$page.url.pathname.includes('/workspace/models')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
								href="/workspace/models">{$i18n.t('Models')}</a
							>
						{/if}

						<!-- Knowledge is admin-only (students never see this tab) -->
						{#if $user?.role === 'admin'}
							<a
								class="min-w-fit p-1.5 {$page.url.pathname.includes('/workspace/knowledge')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
								href="/workspace/knowledge"
							>
								{$i18n.t('Knowledge')}
							</a>
						{/if}

						{#if $user?.role === 'admin' || $user?.permissions?.workspace?.tools}
							<a
								class="min-w-fit p-1.5 {$page.url.pathname.includes('/workspace/tools')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
								href="/workspace/tools"
							>
								{$i18n.t('Tools')}
							</a>
						{/if}
						<!-- Functions (admin-only) -->
						<!---
						{#if $user?.role === 'admin'}
							<a
								class="min-w-fit p-1.5 {$page.url.pathname.includes('/workspace/functions')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
								href="/workspace/functions"
							>
								{$i18n.t('Functions')}
							</a>
						{/if}
						--->
						{#if $user?.role === 'admin' || $chatContext?.context_type === 'lab'}
							<a
								class="min-w-fit p-1.5 {$page.url.pathname.includes('/workspace/lab-resources')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
								href="/workspace/lab-resources"
							>
								{$i18n.t('Lab Resources')}
							</a>
						{/if}

						<!-- My Uploads (visible to both roles) -->
						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/workspace/my-uploads')
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
							href="/workspace/my-uploads"
						>
							{$i18n.t('My Uploads')}
						</a>
					</div>
				</div>

				<!-- <div class="flex items-center text-xl font-semibold">{$i18n.t('Workspace')}</div> -->
			</div>
		</nav>

		<div class="  pb-1 px-[18px] flex-1 max-h-full overflow-y-auto" id="workspace-container">
			<slot />
		</div>
	</div>
{/if}
