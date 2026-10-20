import type { ColumnDef } from "@tanstack/table-core";
import { createRawSnippet } from "svelte";
import { renderSnippet, renderComponent } from "$lib/components/ui/data-table/index.js";
import { Badge } from "$lib/components/ui/badge/index.js";
import DataTableActions from "./data-table-actions.svelte";
import DataTableCheckbox from "./data-table-checkbox.svelte";

export type Task = {
	id: string;
	title: string;
	description: string;
	project: string;
	status: "Pending" | "In Progress" | "Completed" | "On Hold";
	task_type: string;
	link: string;
	assignee: string;
	due_date: string;
};

export const columns: ColumnDef<Task>[] = [
	{
		id: "select",
		header: ({ table }) =>
			renderComponent(DataTableCheckbox, {
				checked: table.getIsAllPageRowsSelected(),
				indeterminate:
					table.getIsSomePageRowsSelected() &&
					!table.getIsAllPageRowsSelected(),
				onCheckedChange: (value) => table.toggleAllPageRowsSelected(!!value),
				"aria-label": "Select all",
			}),
		cell: ({ row }) =>
			renderComponent(DataTableCheckbox, {
				checked: row.getIsSelected(),
				onCheckedChange: (value) => row.toggleSelected(!!value),
				"aria-label": "Select row",
			}),
		enableSorting: false,
		enableHiding: false,
	},
	{
		accessorKey: "title",
		header: "Title",
		cell: ({ row }) => {
			const titleSnippet = createRawSnippet<[{ title: string; description: string }]>(
				(getTask) => {
					const { title, description } = getTask();
					return {
						render: () => `
							<div class="font-medium">${title}</div>
							<div class="text-muted-foreground text-xs">${description}</div>
						`,
					};
				}
			);
			return renderSnippet(titleSnippet, {
				title: row.original.title,
				description: row.original.description,
			});
		},
	},
	{
		accessorKey: "project",
		header: "Project",
		cell: ({ row }) => {
			const projectSnippet = createRawSnippet<[{ project: string }]>(
				(getProject) => {
					const { project } = getProject();
					return {
						render: () => `<div class="text-muted-foreground">${project}</div>`,
					};
				}
			);
			return renderSnippet(projectSnippet, {
				project: row.original.project,
			});
		},
	},
	{
		accessorKey: "task_type",
		header: "Type",
		cell: ({ row }) => {
			const typeSnippet = createRawSnippet<[{ task_type: string }]>(
				(getType) => {
					const { task_type } = getType();
					return {
						render: () => `<div class="text-muted-foreground">${task_type}</div>`,
					};
				}
			);
			return renderSnippet(typeSnippet, {
				task_type: row.original.task_type,
			});
		},
	},
	{
		accessorKey: "status",
		header: "Status",
		cell: ({ row }) => {
			const statusVariants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
				Completed: "default",
				"In Progress": "secondary",
				Pending: "outline",
				"On Hold": "outline",
			};
			const variant = statusVariants[row.original.status] || "outline";
			const statusSnippet = createRawSnippet(() => ({
				render: () => row.original.status,
			}));
			return renderComponent(Badge, { variant, class: "rounded-none", children: statusSnippet });
		},
	},
	{
		accessorKey: "assignee",
		header: "Assignee",
		cell: ({ row }) => {
			const assigneeSnippet = createRawSnippet<[{ assignee: string }]>(
				(getAssignee) => {
					const { assignee } = getAssignee();
					return {
						render: () => `<div class="text-muted-foreground">${assignee}</div>`,
					};
				}
			);
			return renderSnippet(assigneeSnippet, {
				assignee: row.original.assignee,
			});
		},
	},
	{
		accessorKey: "due_date",
		header: "Due Date",
		cell: ({ row }) => {
			const dueDateSnippet = createRawSnippet<[{ due_date: string }]>(
				(getDueDate) => {
					const { due_date } = getDueDate();
					return {
						render: () => `<div class="text-muted-foreground">${due_date}</div>`,
					};
				}
			);
			return renderSnippet(dueDateSnippet, {
				due_date: row.original.due_date,
			});
		},
	},
	{
		id: "actions",
		enableHiding: false,
		cell: ({ row }) => renderComponent(DataTableActions, { id: row.original.id }),
	},
];
