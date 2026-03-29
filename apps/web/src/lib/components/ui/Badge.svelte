<script lang="ts">
  type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';
  type Status = 'active' | 'inactive' | 'pending' | 'failed' | 'running';

  interface BadgeProps {
    severity?: Severity;
    status?: Status;
    label?: string;
    dot?: boolean;
  }

  const SEVERITY_CLASSES: Record<Severity, { bg: string; dot: string; text: string }> = {
    critical: { bg: 'bg-severity-critical-light', dot: 'bg-severity-critical', text: 'text-severity-critical-text' },
    high: { bg: 'bg-severity-high-light', dot: 'bg-severity-high', text: 'text-severity-high-text' },
    medium: { bg: 'bg-severity-medium-light', dot: 'bg-severity-medium', text: 'text-severity-medium-text' },
    low: { bg: 'bg-severity-low-light', dot: 'bg-severity-low', text: 'text-severity-low-text' },
    info: { bg: 'bg-severity-info-light', dot: 'bg-severity-info', text: 'text-severity-info-text' },
  };

  const STATUS_CLASSES: Record<Status, { bg: string; dot: string; text: string }> = {
    active: { bg: 'bg-status-active-light', dot: 'bg-status-active', text: 'text-status-active-text' },
    inactive: { bg: 'bg-status-inactive-light', dot: 'bg-status-inactive', text: 'text-status-inactive-text' },
    pending: { bg: 'bg-status-pending-light', dot: 'bg-status-pending', text: 'text-status-pending-text' },
    failed: { bg: 'bg-status-failed-light', dot: 'bg-status-failed', text: 'text-status-failed-text' },
    running: { bg: 'bg-status-running-light', dot: 'bg-status-running', text: 'text-status-running-text' },
  };

  const NEUTRAL_CLASSES = { bg: 'bg-neutral-100', dot: 'bg-neutral-500', text: 'text-neutral-700' };

  let { severity, status, label, dot = true }: BadgeProps = $props();

  let colors = $derived.by(() => {
    if (severity && severity in SEVERITY_CLASSES) {
      return SEVERITY_CLASSES[severity];
    }
    if (status && status in STATUS_CLASSES) {
      return STATUS_CLASSES[status];
    }
    return NEUTRAL_CLASSES;
  });

  let displayLabel = $derived(label ?? severity ?? status ?? '');
</script>

<span
  class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium {colors.bg} {colors.text}"
>
  {#if dot}
    <span class="h-1.5 w-1.5 rounded-full {colors.dot}"></span>
  {/if}
  {displayLabel}
</span>
