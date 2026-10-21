<script lang="ts">
  import type { HTMLButtonAttributes } from "svelte/elements";
  import type { PlannerActivity } from "$lib/workspaces/types";
  import { cn } from "$lib/utils.js";

  type CalendarCellData = {
    date: Date;
    key: string;
    inMonth: boolean;
    activities: PlannerActivity[];
  };

  let {
    cell,
    selected = false,
    today = false,
    class: className,
    ...rest
  }: HTMLButtonAttributes & {
    cell: CalendarCellData;
    selected?: boolean;
    today?: boolean;
    class?: string;
  } = $props();
</script>

<button
  type="button"
  class={cn("calendar-cell group text-left transition", className)}
  class:outside={!cell.inMonth}
  class:selected
  class:today
  aria-label="{cell.date.toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
  })}, {cell.activities.length} activities"
  aria-pressed={selected}
  {...rest}
>
  <span class="day-number">{cell.date.getDate()}</span>
  {#if cell.activities.length > 0}
    <span class="task-indicators">
      {#each cell.activities as activity (activity.id)}
        <span
          class="task-pill"
          style="--task-color: {activity.workspace.color}"
          title={activity.title}
        >
          <span class="task-pill-dot"></span>
          <span class="hidden truncate sm:inline">{activity.title}</span>
        </span>
      {/each}
    </span>
  {/if}
</button>

<style>
  .calendar-cell {
    position: relative;
    min-width: 0;
    min-height: 7.2rem;
    padding: 0.6rem 0.55rem 0.5rem;
    border-right: 1px solid var(--color-base-300);
    border-bottom: 1px solid var(--color-base-300);
    background: var(--color-base-100);
  }

  .calendar-cell:nth-child(7n) {
    border-right: 0;
  }

  .calendar-cell:hover {
    background: var(--color-base-200);
  }

  .calendar-cell.outside {
    background: var(--color-base-200);
  }

  .calendar-cell.outside .day-number {
    color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
  }

  .calendar-cell.selected {
    z-index: 1;
    box-shadow: inset 0 0 0 2px var(--color-primary);
  }

  .day-number {
    position: absolute;
    top: 0.6rem;
    left: 0.55rem;
    display: inline-flex;
    width: 1.7rem;
    height: 1.7rem;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    color: var(--color-base-content);
    font-size: 0.75rem;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }

  .calendar-cell.today .day-number {
    background: var(--color-primary);
    color: var(--color-primary-content);
  }

  .calendar-cell.selected .day-number {
    color: var(--color-base-content);
    font-weight: 800;
  }

  .calendar-cell.today.selected .day-number {
    background: var(--color-primary);
    color: var(--color-primary-content);
  }

  .task-indicators {
    display: flex;
    flex-direction: column;
    gap: 3px;
    margin-top: 1.98rem;
  }

  .task-pill {
    display: flex;
    min-width: 0;
    height: 1.2rem;
    align-items: center;
    gap: 0.3rem;
    overflow: hidden;
    border-radius: var(--radius-selector);
    padding: 0 0.25rem;
    background: color-mix(
      in oklab,
      var(--task-color) 38%,
      var(--color-base-100)
    );
    color: var(--color-base-content);
    font-size: 0.6rem;
    line-height: 1;
  }

  .task-pill:hover {
    background: color-mix(
      in oklab,
      var(--task-color) 55%,
      var(--color-base-100)
    );
  }

  .task-pill-dot {
    width: 0.32rem;
    height: 0.32rem;
    flex: 0 0 0.32rem;
    border-radius: 50%;
    background: var(--task-color);
  }

  @media (max-width: 639px) {
    .calendar-cell {
      min-height: 4.65rem;
      padding: 0.28rem;
      text-align: left;
    }

    .day-number {
      top: 0.28rem;
      left: 0.28rem;
      width: 1.55rem;
      height: 1.55rem;
    }

    .task-indicators {
      min-height: 0.35rem;
      flex-direction: row;
      flex-wrap: wrap;
      justify-content: flex-start;
      gap: 2px;
      margin-top: 1.55rem;
    }

    .task-pill {
      width: 0.32rem;
      height: 0.32rem;
      padding: 0;
      background: var(--task-color);
    }

    .task-pill-dot {
      display: none;
    }
  }
</style>
