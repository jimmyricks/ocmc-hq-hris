import adapter from '@sveltejs/adapter-node';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

const API_URL = process.env.API_URL ?? 'http://localhost:8005';

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter: adapter()
		})
	],
	ssr: {
		noExternal: ['@lucide/svelte']
	},
	server: {
		proxy: {
			'/api': {
				target: API_URL,
				changeOrigin: true,
				secure: false
			},
			'/uploads': {
				target: API_URL,
				changeOrigin: true,
				secure: false
			}
		}
	}
});
