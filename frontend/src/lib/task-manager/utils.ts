import type { Priority, TaskStatus, WorkflowState } from './types.js';

export const STATUS_META: Record<
	TaskStatus,
	{ label: string; variant: 'default' | 'primary' | 'secondary' | 'destructive' | 'outline' | 'ghost' | 'info' | 'success' | 'warning'; color: string }
> = {
	pending: { label: 'Pending', variant: 'outline', color: 'var(--color-base-content)' },
	in_progress: { label: 'In Progress', variant: 'primary', color: 'var(--color-primary)' },
	for_review: { label: 'For Review', variant: 'warning', color: 'var(--color-warning)' },
	submitted: { label: 'Submitted', variant: 'warning', color: 'var(--color-warning)' },
	needs_revision: { label: 'Needs Revision', variant: 'destructive', color: 'var(--color-error)' },
	approved: { label: 'Approved', variant: 'success', color: 'var(--color-success)' },
	closed: { label: 'Closed', variant: 'success', color: 'var(--color-success)' },
	cancelled: { label: 'Cancelled', variant: 'outline', color: 'var(--color-base-content)' },
};

// workflow_state IS the task status. See user-journey.md Journey 7.
export const WORKFLOW_STATE_META: Record<
	WorkflowState,
	{ label: string; variant: 'default' | 'primary' | 'secondary' | 'destructive' | 'outline' | 'info' | 'success' | 'warning'; color: string }
> = {
	draft_assigned: { label: 'Draft', variant: 'outline', color: 'var(--color-base-content)' },
	in_progress: { label: 'In Progress', variant: 'primary', color: 'var(--color-primary)' },
	for_review: { label: 'For Review', variant: 'warning', color: 'var(--color-warning)' },
	needs_revision: { label: 'Needs Revision', variant: 'destructive', color: 'var(--color-error)' },
	approved: { label: 'Approved', variant: 'success', color: 'var(--color-success)' },
	closed: { label: 'Closed', variant: 'success', color: 'var(--color-success)' },
};

// Map a task record to its effective workflow state, falling back to legacy `status`.
export function taskState(task: { workflow_state?: WorkflowState; status: TaskStatus }): WorkflowState | TaskStatus {
	const state = task.workflow_state ?? task.status;
	return state === 'submitted' ? 'for_review' : state;
}

export function stateLabel(task: { workflow_state?: WorkflowState; status: TaskStatus }): string {
	const state = taskState(task);
	if (state in WORKFLOW_STATE_META) {
		return WORKFLOW_STATE_META[state as WorkflowState].label;
	}
	return STATUS_META[state as TaskStatus]?.label ?? String(state);
}

export function stateBadge(task: { workflow_state?: WorkflowState; status: TaskStatus }): {
	label: string;
	variant: 'default' | 'primary' | 'secondary' | 'destructive' | 'outline' | 'ghost' | 'info' | 'success' | 'warning';
	color: string;
} {
	const state = taskState(task);
	if (state in WORKFLOW_STATE_META) {
		return WORKFLOW_STATE_META[state as WorkflowState];
	}
	const meta = STATUS_META[state as TaskStatus];
	return meta ?? { label: String(state), variant: 'outline' as const, color: 'var(--color-base-content)' };
}

export const PRIORITY_META: Record<Priority, { label: string; color: string }> = {
	urgent: { label: 'Urgent', color: 'var(--color-error)' },
	high: { label: 'High', color: 'var(--color-warning)' },
	medium: { label: 'Medium', color: 'var(--color-info)' },
	low: { label: 'Low', color: 'var(--color-primary)' },
};

export function prioritySort(a: Priority, b: Priority): number {
	const order: Priority[] = ['urgent', 'high', 'medium', 'low'];
	return order.indexOf(a) - order.indexOf(b);
}

export function statusSort(a: TaskStatus, b: TaskStatus): number {
	const order: TaskStatus[] = ['pending', 'in_progress', 'for_review', 'submitted', 'needs_revision', 'approved', 'closed', 'cancelled'];
	return order.indexOf(a) - order.indexOf(b);
}

export function initials(name: string): string {
	return name
		.split(' ')
		.map((p) => p[0])
		.filter(Boolean)
		.slice(0, 2)
		.join('')
		.toUpperCase();
}

export function formatDueDate(iso: string | null | undefined): {
	relative: string;
	absolute: string;
	isOverdue: boolean;
} {
	if (!iso) {
		return { relative: 'No due date', absolute: '', isOverdue: false };
	}
	const date = new Date(iso);
	const now = new Date();
	now.setHours(0, 0, 0, 0);
	const target = new Date(date);
	target.setHours(0, 0, 0, 0);

	const diffDays = Math.round((target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

	let relative = '';
	if (diffDays === 0) relative = 'Today';
	else if (diffDays === 1) relative = 'Tomorrow';
	else if (diffDays === -1) relative = 'Yesterday';
	else if (diffDays > 1 && diffDays <= 6) {
		relative = date.toLocaleDateString('en-US', { weekday: 'long' });
	} else if (diffDays < -1 && diffDays >= -6) {
		relative = `${Math.abs(diffDays)} days ago`;
	} else {
		relative = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	}

	const absolute = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	const isOverdue = diffDays < 0;

	return { relative: relative || absolute, absolute, isOverdue };
}

export function formatTimestamp(iso: string): string {
	const date = new Date(iso);
	return date.toLocaleString('en-US', {
		month: 'short',
		day: 'numeric',
		hour: 'numeric',
		minute: '2-digit',
	});
}

/**
 * Compact relative time formatter, e.g. "3m", "4h", "1w", "2y".
 * Falls back to absolute short date for anything older than a year.
 */
export function timeAgo(iso: string | null | undefined): string {
	if (!iso) return '';
	const date = new Date(iso);
	const now = Date.now();
	const seconds = Math.round((now - date.getTime()) / 1000);

	if (seconds < 45) return 'now';
	const minutes = Math.round(seconds / 60);
	if (minutes < 60) return `${minutes}m`;
	const hours = Math.round(minutes / 60);
	if (hours < 24) return `${hours}h`;
	const days = Math.round(hours / 24);
	if (days < 7) return `${days}d`;
	const weeks = Math.round(days / 7);
	if (weeks < 5) return `${weeks}w`;
	const months = Math.round(days / 30);
	if (months < 12) return `${months}mo`;
	const years = Math.floor(days / 365);
	if (years >= 1) return `${years}y`;
	return shortDate(iso);
}

export function shortDate(iso: string): string {
	return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function todayISO(): string {
	return new Date().toISOString().split('T')[0];
}

export function addDays(days: number): string {
	const d = new Date();
	d.setDate(d.getDate() + days);
	return d.toISOString().split('T')[0];
}
