<script lang="ts">
  import type { HTMLInputAttributes } from "svelte/elements";

  type Props = Omit<HTMLInputAttributes, "class" | "value"> & {
    value?: string | number;
    class?: string;
  };

  let { value = $bindable(""), class: className = "", ...rest }: Props = $props();
</script>

<input class="ds-input {className}" bind:value {...rest} />

<style>
  .ds-input {
    width: 100%;
    min-height: 39px;
    border: 1px solid #cbd3df;
    border-radius: 8px;
    background: #fff;
    padding: 0 11px;
    color: #202a38;
    font-size: 13px;
    transition: border-color 130ms ease, box-shadow 130ms ease;
  }
  .ds-input::placeholder {
    color: #8b96a6;
  }
  .ds-input:hover {
    border-color: #aeb9c9;
  }
  .ds-input:focus {
    border-color: #2457d6;
    outline: 3px solid rgb(120 149 232 / 22%);
  }
  .ds-input:disabled {
    background: #f0f3f7;
    color: #7a8798;
  }
</style>
