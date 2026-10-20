import type { ApprovalDecision, Comment, Project, ProjectMember, Task, TaskAssignment, TaskApproval, TaskCategory, TaskSubmission, TaskType, User, WorkflowProgress } from './types.js';
import { apiJSON, listEntity, listFiltered, getEntityRecord, saveEntity, deleteEntity } from '$lib/api/index.js';

export const taskApi = {
	async getCurrentUser(): Promise<User> {
		const res = await apiJSON('/api/profile');
		return res.data as User;
	},

	async getUsers(): Promise<User[]> {
		const res = await apiJSON('/api/workspaces/directory');
		return (res.data ?? []) as User[];
	},

	async getProjects(): Promise<Project[]> {
		const res = await listEntity('project', 1, 100);
		return (res.data ?? []) as Project[];
	},

	async getProject(id: string): Promise<Project | undefined> {
		const res = await getEntityRecord('project', id);
		return res.data as Project | undefined;
	},

	async getAllProjectsWithMeta(): Promise<Project[]> {
		return this.getProjects();
	},

	async getTaskTypes(): Promise<TaskType[]> {
		const res = await listEntity('task_type', 1, 100);
		return (res.data ?? []) as TaskType[];
	},

	async getTaskCategories(): Promise<TaskCategory[]> {
		const res = await listEntity('task_category', 1, 100);
		return (res.data ?? []) as TaskCategory[];
	},

	async getTasksForProject(projectId: string | null): Promise<Task[]> {
		if (!projectId || projectId === 'all') {
			const res = await listEntity('task', 1, 100);
			return (res.data ?? []) as Task[];
		}
		const res = await listFiltered('task', [{ field: 'project_id', op: 'eq', value: projectId }], 1, 100);
		return (res.data ?? []) as Task[];
	},

	async getTask(id: string): Promise<Task | undefined> {
		const res = await getEntityRecord('task', id);
		return res.data as Task | undefined;
	},

	async updateTask(updated: Task): Promise<Task> {
		const res = await saveEntity('task', updated, updated.id);
		return res.data as Task;
	},

	async addTask(task: Omit<Task, 'id'>): Promise<Task> {
		const res = await saveEntity('task', task);
		return res.data as Task;
	},

	// Dedicated endpoint: generates task key + audit log, sets workflow_state.
	async createTask(payload: {
		project_id: string;
		task_type_id: string;
		title: string;
		category_id?: string;
		priority?: string;
		due_date?: string;
		planned_start_at?: string;
		planned_end_at?: string;
		description?: string;
	}): Promise<Task> {
		const res = await apiJSON('/api/project-tasks/tasks', {
			method: 'POST',
			body: JSON.stringify(payload),
		});
		return res.data as Task;
	},

	async assignTask(taskId: string, userId: string): Promise<TaskAssignment> {
		const res = await apiJSON(`/api/project-tasks/tasks/${taskId}/assign`, {
			method: 'POST',
			body: JSON.stringify({ user_id: userId }),
		});
		return res.data as TaskAssignment;
	},

	async deleteTask(id: string): Promise<void> {
		await deleteEntity('task', id);
	},

	// --- Project members (security boundary: only members can be assigned tasks) ---
	async getProjectMembers(projectId: string): Promise<ProjectMember[]> {
		const res = await listFiltered('project_member', [
			{ field: 'project_id', op: 'eq', value: projectId },
		], 1, 100);
		return (res.data ?? []) as ProjectMember[];
	},

	async addProjectMember(projectId: string, userId: string, role?: string): Promise<ProjectMember> {
		const res = await saveEntity('project_member', {
			project_id: projectId,
			user_id: userId,
			role: role ?? 'member',
		});
		return res.data as ProjectMember;
	},

	async removeProjectMember(memberId: string): Promise<void> {
		await deleteEntity('project_member', memberId);
	},

	// --- Comments (per-task conversation thread) ---
	async getComments(taskId: string): Promise<Comment[]> {
		const res = await apiJSON(`/api/features/comments/task/${taskId}`);
		return (res.data ?? []) as Comment[];
	},

	async addComment(taskId: string, body: string): Promise<Comment> {
		const res = await apiJSON(`/api/features/comments/task/${taskId}`, {
			method: 'POST',
			body: JSON.stringify({ body }),
		});
		return res.data as Comment;
	},

	async updateComment(taskId: string, commentId: string, body: string): Promise<Comment> {
		const res = await apiJSON(`/api/features/comments/task/${taskId}/${commentId}`, {
			method: 'PUT',
			body: JSON.stringify({ body }),
		});
		return res.data as Comment;
	},

	async deleteComment(taskId: string, commentId: string): Promise<void> {
		await apiJSON(`/api/features/comments/task/${taskId}/${commentId}`, { method: 'DELETE' });
	},

	async getTaskAssignments(taskId: string): Promise<TaskAssignment[]> {
		const res = await apiJSON(`/api/project-tasks/tasks/${taskId}/assignments`);
		// Backend wraps paginated result: { data: { data: [...], total, page, page_size } }
		const inner = res.data;
		if (Array.isArray(inner)) return inner as TaskAssignment[];
		if (inner && Array.isArray(inner.data)) return inner.data as TaskAssignment[];
		return [];
	},

	async getSubmissionsForAssignment(assignmentId: string): Promise<TaskSubmission[]> {
		const res = await listFiltered('task_submission', [{ field: 'task_assignment_id', op: 'eq', value: assignmentId }], 1, 100);
		return (res.data ?? []) as TaskSubmission[];
	},

	async getSubmissionsForTask(taskId: string): Promise<TaskSubmission[]> {
		const assignments = await this.getTaskAssignments(taskId);
		const all: TaskSubmission[] = [];
		for (const a of assignments) {
			const subs = await this.getSubmissionsForAssignment(a.id);
			all.push(...subs);
		}
		return all.sort((a, b) => (b.version ?? 0) - (a.version ?? 0));
	},

	async submitWork(payload: {
		task_assignment_id: string;
		notes?: string;
		external_link?: string;
		previous_submission_id?: string;
	}): Promise<TaskSubmission> {
		const res = await apiJSON('/api/project-tasks/submissions', {
			method: 'POST',
			body: JSON.stringify(payload),
		});
		return res.data as TaskSubmission;
	},

	async approveSubmission(
		submissionId: string,
		decision: ApprovalDecision,
		remarks?: string,
	): Promise<TaskApproval> {
		const res = await apiJSON(`/api/project-tasks/submissions/${submissionId}/approve`, {
			method: 'POST',
			body: JSON.stringify({ decision, remarks }),
		});
		return res.data as TaskApproval;
	},

	// --- Workflow engine ---
	async getWorkflowProgress(entity: string, recordId: string): Promise<WorkflowProgress> {
		const res = await apiJSON(`/api/entity/${entity}/${recordId}/workflow-progress`);
		return res.data as WorkflowProgress;
	},

	async executeWorkflowTransition(entity: string, payload: {
		record_id: string;
		action: string;
	}): Promise<any> {
		const res = await apiJSON(`/api/entity/${entity}/workflow`, {
			method: 'POST',
			body: JSON.stringify(payload),
		});
		return res.data;
	},
};

// No-op helpers kept for backwards compatibility while the UI is migrated.
export function _setCurrentUserRole(_role: string) {
	// auth state is now managed by the backend session/JWT
}

export async function _getAllTasks(): Promise<Task[]> {
	const res = await listEntity('task', 1, 100);
	return (res.data ?? []) as Task[];
}
