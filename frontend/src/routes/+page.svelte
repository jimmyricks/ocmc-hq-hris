<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { getToken } from '$lib/auth';

	onMount(() => {
		goto(getToken() ? '/dashboard' : '/login');
	});
</script>

<div class="flex h-screen items-center justify-center">
	<p class="text-muted-foreground">Loading...</p>
</div>
