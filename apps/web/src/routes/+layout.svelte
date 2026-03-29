<script lang="ts">
  /**
   * T012: Root layout — uses server-side auth data from hooks.server.ts.
   * No more client-side OAuth guard. Auth is handled by server hooks.
   */
  import '../app.css';

  let { children, data: _data } = $props();
</script>

{@render children()}
