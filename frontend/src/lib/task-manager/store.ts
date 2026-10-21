import { writable } from 'svelte/store';
import type { Project, Task, User } from './types.js';

export interface TaskManagerState {
	selectedProjectId: string;
	currentUser: User | null;
	allProject: Project;
	projects: Project[];
	tasks: Task[];
	loading: boolean;
	searchQuery: string;
}

export const taskManagerStore = writable<TaskManagerState>({
	selectedProjectId: 'all',
	currentUser: null,
	allProject: { id: 'all', name: 'All Tasks', color: 'var(--color-base-content)', icon: 'layers', manager_id: '' },
	projects: [],
	tasks: [],
	loading: true,
	searchQuery: '',
});
