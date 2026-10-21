<script lang="ts">
  import { browser } from "$app/environment";
  import { goto } from "$app/navigation";
  import { toast } from "$lib/notifications";
  import { payrollApi } from "$lib/payroll/api.js";
  import type { PayrollPeriod, PayrollSettings } from "$lib/payroll/types.js";
  import { getToken } from "$lib/auth";
  import { OFFICIAL_CURRENCY } from "$lib/constants.js";

  import * as Card from "$lib/components/ui/card/index.js";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import * as Field from "$lib/components/ui/field/index.js";
  import * as Select from "$lib/components/ui/select/index.js";
  import * as Empty from "$lib/components/ui/empty/index.js";
  import * as Item from "$lib/components/ui/item/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { Separator } from "$lib/components/ui/separator/index.js";
  import { Skeleton } from "$lib/components/ui/skeleton/index.js";
  import { Switch } from "$lib/components/ui/switch/index.js";
  import { Label } from "$lib/components/ui/label/index.js";

  import PlusIcon from "@lucide/svelte/icons/plus";
  import SettingsIcon from "@lucide/svelte/icons/settings";
  import BanknoteIcon from "@lucide/svelte/icons/banknote";
  import ChevronRightIcon from "@lucide/svelte/icons/chevron-right";
  import CalendarIcon from "@lucide/svelte/icons/calendar";

  // ── State ────────────────────────────────────────────────────────────
  let periods = $state<PayrollPeriod[]>([]);
  let loading = $state(true);
  let error = $state("");

  // Create period dialog
  let createOpen = $state(false);
  let creating = $state(false);
  let newPeriod = $state({
    label: "",
    start_date: "",
    end_date: "",
    cutoff: "",
  });

  // Settings dialog
  let settingsOpen = $state(false);
  let settingsSaving = $state(false);
  let settings = $state<PayrollSettings>({
    currency: OFFICIAL_CURRENCY,
    cutoff_rule: "bi_monthly",
    auto_approve_threshold: 0,
    require_hr_approval: true,
    notify_users_on_payment: true,
    default_period_start_day: 1,
    default_period_end_day: 15,
  });
  let settingsId = $state<string | undefined>(undefined);

  // ── Constants ────────────────────────────────────────────────────────
  const PERIOD_STATUS_META: Record<
    string,
    { label: string; variant: "outline" | "secondary" | "default" }
  > = {
    open: { label: "Open", variant: "outline" },
    closed: { label: "Closed", variant: "secondary" },
    paid: { label: "Paid", variant: "default" },
  };

  const CURRENCIES = [OFFICIAL_CURRENCY];
  const CUTOFF_RULES = [
    { value: "bi_monthly", label: "Bi-monthly (1-15, 16-end)" },
    { value: "monthly", label: "Monthly" },
    { value: "weekly", label: "Weekly" },
  ];

  // ── Helpers ──────────────────────────────────────────────────────────
  function formatDate(d?: string): string {
    if (!d) return "—";
    return d.split("T")[0];
  }

  // ── Lifecycle ────────────────────────────────────────────────────────
  $effect(() => {
    if (!browser) return;
    if (!getToken()) {
      goto("/login");
      return;
    }
    loadPeriods();
    loadSettings();
  });

  async function loadPeriods() {
    loading = true;
    error = "";
    try {
      periods = await payrollApi.getPeriods();
    } catch (err: any) {
      error = err.message || "Failed to load payroll periods";
    } finally {
      loading = false;
    }
  }

  async function loadSettings() {
    try {
      const s = await payrollApi.getSettings();
      if (s) {
        settingsId = s.id;
        settings = {
          currency: OFFICIAL_CURRENCY,
          cutoff_rule: s.cutoff_rule ?? "bi_monthly",
          auto_approve_threshold: Number(s.auto_approve_threshold) || 0,
          require_hr_approval: s.require_hr_approval ?? true,
          notify_users_on_payment: s.notify_users_on_payment ?? true,
          default_period_start_day: s.default_period_start_day ?? 1,
          default_period_end_day: s.default_period_end_day ?? 15,
        };
      }
    } catch {
      // No settings yet — defaults remain
    }
  }

  // ── Create period ────────────────────────────────────────────────────
  function openCreateDialog() {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth() + 1;
    const startDay = settings.default_period_start_day;
    const endDay = settings.default_period_end_day;
    const startDate = `${year}-${String(month).padStart(2, "0")}-${String(startDay).padStart(2, "0")}`;
    const endDate = `${year}-${String(month).padStart(2, "0")}-${String(endDay).padStart(2, "0")}`;
    newPeriod = {
      label: `${now.toLocaleString("en-US", { month: "long" })} ${startDay}-${endDay}, ${year}`,
      start_date: startDate,
      end_date: endDate,
      cutoff: endDate,
    };
    createOpen = true;
  }

  function updatePeriodLabel() {
    if (newPeriod.start_date && newPeriod.end_date) {
      newPeriod.label = `${newPeriod.start_date} → ${newPeriod.end_date}`;
    }
  }

  async function handleCreate() {
    if (!newPeriod.start_date || !newPeriod.end_date) {
      toast.error("Start and end dates are required");
      return;
    }
    if (newPeriod.start_date > newPeriod.end_date) {
      toast.error("Start date must be before end date");
      return;
    }
    creating = true;
    try {
      await payrollApi.createPeriod({
        label: newPeriod.label || undefined,
        start_date: newPeriod.start_date,
        end_date: newPeriod.end_date,
        cutoff: newPeriod.cutoff || newPeriod.end_date,
      });
      createOpen = false;
      await loadPeriods();
      toast.success("Payroll period created");
    } catch (err: any) {
      toast.error(err.message || "Failed to create payroll period");
    } finally {
      creating = false;
    }
  }

  // ── Settings ─────────────────────────────────────────────────────────
  async function handleSaveSettings() {
    settingsSaving = true;
    try {
      const saved = await payrollApi.saveSettings(
        {
          currency: settings.currency,
          cutoff_rule: settings.cutoff_rule,
          auto_approve_threshold: Number(settings.auto_approve_threshold) || 0,
          require_hr_approval: settings.require_hr_approval,
          notify_users_on_payment: settings.notify_users_on_payment,
          default_period_start_day:
            Number(settings.default_period_start_day) || 1,
          default_period_end_day: Number(settings.default_period_end_day) || 15,
        },
        settingsId,
      );
      settingsId = saved.id;
      toast.success("Payroll settings saved");
      settingsOpen = false;
    } catch (err: any) {
      toast.error(err.message || "Failed to save settings");
    } finally {
      settingsSaving = false;
    }
  }
</script>

<div class="flex flex-col gap-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Payroll</h1>
      <p class="text-sm text-base-content/60">
        Generate, review, and disburse payroll per user.
      </p>
    </div>
    <div class="flex gap-2">
      <Button
        variant="outline"
        onclick={() => (settingsOpen = true)}
        class="gap-1.5"
      >
        <SettingsIcon class="size-4" />
        Settings
      </Button>
      <Button onclick={openCreateDialog} class="gap-1.5">
        <PlusIcon class="size-4" />
        New Period
      </Button>
    </div>
  </div>

  {#if error}
    <p class="rounded-md bg-error/10 p-3 text-sm text-error">
      {error}
    </p>
  {/if}

  <!-- Periods list -->
  {#if loading}
    <Item.Group>
      {#each Array.from({ length: 3 }) as _, i (i)}
        <Item.Root variant="outline">
          <Item.Media variant="icon"><Skeleton class="size-5" /></Item.Media>
          <Item.Content>
            <Item.Title><Skeleton class="h-4 w-40" /></Item.Title>
            <Item.Description><Skeleton class="h-3 w-28" /></Item.Description>
          </Item.Content>
          <Item.Actions><Skeleton class="h-5 w-12" /></Item.Actions>
        </Item.Root>
      {/each}
    </Item.Group>
  {:else if periods.length === 0}
    <Card.Root>
      <Card.Content class="pt-6">
        <Empty.Root>
          <Empty.Media variant="icon"><BanknoteIcon /></Empty.Media>
          <Empty.Header>
            <Empty.Title>No payroll periods</Empty.Title>
            <Empty.Description>
              Create a bi-monthly payroll period to get started. Generation will
              scan approved submissions, create per-user entries, and auto-close
              tasks.
            </Empty.Description>
          </Empty.Header>
        </Empty.Root>
      </Card.Content>
    </Card.Root>
  {:else}
    <Item.Group>
      {#each periods as period (period.id)}
        {@const ps =
          PERIOD_STATUS_META[period.status] ?? PERIOD_STATUS_META.open}
        <Item.Root variant="outline">
          {#snippet child({ props })}
            <a href={`/payroll/${period.id}`} {...props}>
              <Item.Media variant="icon"><CalendarIcon /></Item.Media>
              <Item.Content>
                <Item.Title>{period.label}</Item.Title>
                <Item.Description>
                  {formatDate(period.start_date)} → {formatDate(
                    period.end_date,
                  )}
                </Item.Description>
              </Item.Content>
              <Item.Actions>
                <Badge variant={ps.variant}>{ps.label}</Badge>
                <ChevronRightIcon class="size-4 text-base-content/60" />
              </Item.Actions>
            </a>
          {/snippet}
        </Item.Root>
      {/each}
    </Item.Group>
  {/if}
</div>

<!-- ── Create Period Dialog ─────────────────────────────────────────── -->
<Dialog.Root bind:open={createOpen}>
  <Dialog.Content class="max-w-lg">
    <Dialog.Header>
      <Dialog.Title>New Payroll Period</Dialog.Title>
      <Dialog.Description
        >Create a bi-monthly payroll period for generating entries.</Dialog.Description
      >
    </Dialog.Header>

    <Field.FieldGroup>
      <Field.Field>
        <Field.Label for="period-label">Label</Field.Label>
        <Input
          id="period-label"
          bind:value={newPeriod.label}
          placeholder="e.g. July 1-15, 2026"
        />
      </Field.Field>

      <div class="grid grid-cols-2 gap-4">
        <Field.Field>
          <Field.Label for="period-start">Start Date</Field.Label>
          <Input
            id="period-start"
            type="date"
            bind:value={newPeriod.start_date}
            oninput={updatePeriodLabel}
          />
        </Field.Field>

        <Field.Field>
          <Field.Label for="period-end">End Date</Field.Label>
          <Input
            id="period-end"
            type="date"
            bind:value={newPeriod.end_date}
            oninput={() => {
              if (!newPeriod.cutoff || newPeriod.cutoff < newPeriod.end_date) {
                newPeriod.cutoff = newPeriod.end_date;
              }
              updatePeriodLabel();
            }}
          />
        </Field.Field>
      </div>

      <Field.Field>
        <Field.Label for="period-cutoff">Cutoff Date</Field.Label>
        <Input id="period-cutoff" type="date" bind:value={newPeriod.cutoff} />
      </Field.Field>
    </Field.FieldGroup>

    <Dialog.Footer>
      <Button variant="outline" onclick={() => (createOpen = false)}
        >Cancel</Button
      >
      <Button disabled={creating} onclick={handleCreate}>
        {creating ? "Creating..." : "Create Period"}
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>

<!-- ── Settings Dialog ──────────────────────────────────────────────── -->
<Dialog.Root bind:open={settingsOpen}>
  <Dialog.Content class="max-w-lg">
    <Dialog.Header>
      <Dialog.Title>Configure Payroll Settings</Dialog.Title>
      <Dialog.Description>
        Default currency, cutoff rules, and approval thresholds for payroll
        generation.
      </Dialog.Description>
    </Dialog.Header>

    <Field.FieldGroup>
      <Field.Field>
        <Field.Label for="settings-currency">Default Currency</Field.Label>
        <Select.Root
          type="single"
          value={settings.currency}
          onValueChange={(v) => (settings.currency = v)}
        >
          <Select.Trigger id="settings-currency" class="w-full"
            >{settings.currency}</Select.Trigger
          >
          <Select.Content>
            {#each CURRENCIES as c (c)}
              <Select.Item value={c} label={c}>{c}</Select.Item>
            {/each}
          </Select.Content>
        </Select.Root>
      </Field.Field>

      <Field.Field>
        <Field.Label for="settings-cutoff">Cutoff Rule</Field.Label>
        <Select.Root
          type="single"
          value={settings.cutoff_rule}
          onValueChange={(v) => (settings.cutoff_rule = v)}
        >
          <Select.Trigger id="settings-cutoff" class="w-full">
            {CUTOFF_RULES.find((r) => r.value === settings.cutoff_rule)
              ?.label ?? settings.cutoff_rule}
          </Select.Trigger>
          <Select.Content>
            {#each CUTOFF_RULES as rule (rule.value)}
              <Select.Item value={rule.value} label={rule.label}
                >{rule.label}</Select.Item
              >
            {/each}
          </Select.Content>
        </Select.Root>
      </Field.Field>

      <div class="grid grid-cols-2 gap-4">
        <Field.Field>
          <Field.Label for="settings-start-day"
            >Default Period Start Day</Field.Label
          >
          <Input
            id="settings-start-day"
            type="number"
            min="1"
            max="31"
            bind:value={settings.default_period_start_day}
          />
        </Field.Field>
        <Field.Field>
          <Field.Label for="settings-end-day"
            >Default Period End Day</Field.Label
          >
          <Input
            id="settings-end-day"
            type="number"
            min="1"
            max="31"
            bind:value={settings.default_period_end_day}
          />
        </Field.Field>
      </div>

      <Separator />

      <Field.Field>
        <Field.Label for="settings-threshold"
          >Auto-approve Threshold</Field.Label
        >
        <Input
          id="settings-threshold"
          type="number"
          min="0"
          bind:value={settings.auto_approve_threshold}
          placeholder="0"
        />
        <Field.Description>
          Entries below this amount are auto-approved during generation. Set to
          0 to require manual approval for all entries.
        </Field.Description>
      </Field.Field>

      <Separator />

      <Field.Field
        data-disabled={false}
        class="flex-row items-center justify-between"
      >
        <div class="flex flex-col gap-0.5">
          <Label for="settings-hr-approval">Require HR Approval</Label>
          <Field.Description
            >Entries must be approved by HR before payment.</Field.Description
          >
        </div>
        <Switch
          id="settings-hr-approval"
          bind:checked={settings.require_hr_approval}
        />
      </Field.Field>

      <Field.Field
        data-disabled={false}
        class="flex-row items-center justify-between"
      >
        <div class="flex flex-col gap-0.5">
          <Label for="settings-notify">Notify Users on Payment</Label>
          <Field.Description
            >Send a notification when payroll is disbursed.</Field.Description
          >
        </div>
        <Switch
          id="settings-notify"
          bind:checked={settings.notify_users_on_payment}
        />
      </Field.Field>
    </Field.FieldGroup>

    <Dialog.Footer>
      <Button variant="outline" onclick={() => (settingsOpen = false)}
        >Cancel</Button
      >
      <Button disabled={settingsSaving} onclick={handleSaveSettings}>
        {settingsSaving ? "Saving..." : "Save Settings"}
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
