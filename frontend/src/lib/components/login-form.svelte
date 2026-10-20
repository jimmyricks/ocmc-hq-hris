<script lang="ts">
  import { Button } from "$lib/components/native/button/index.js";
  import * as Card from "$lib/components/native/card/index.js";
  import { Input } from "$lib/components/native/input/index.js";
  import {
    FieldGroup,
    Field,
    FieldLabel,
    FieldDescription,
    FieldError,
  } from "$lib/components/native/field/index.js";

  const id = $props.id();

  let {
    username = $bindable(""),
    password = $bindable(""),
    loading = false,
    error = "",
    loadingText = "Signing in...",
    buttonText = "Login",
    usernameLabel = "Username",
    usernamePlaceholder = "admin",
    onsubmit,
  }: {
    username?: string;
    password?: string;
    loading?: boolean;
    error?: string;
    loadingText?: string;
    buttonText?: string;
    usernameLabel?: string;
    usernamePlaceholder?: string;
    /** Note: this is the form's onsubmit, not the button's */
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onsubmit?: any;
  } = $props();
</script>

<Card.Root class="mx-auto w-full max-w-sm">
  <Card.Header>
    <Card.Title class="text-2xl">Login</Card.Title>
    <Card.Description
      >Enter your credentials below to login to your account</Card.Description
    >
  </Card.Header>
  <Card.Content>
    <form {onsubmit}>
      <FieldGroup>
        <Field>
          <FieldLabel for="username-{id}">{usernameLabel}</FieldLabel>
          <Input
            id="username-{id}"
            type="text"
            placeholder={usernamePlaceholder}
            required
            bind:value={username}
          />
        </Field>
        <Field>
          <div class="flex items-center">
            <FieldLabel for="password-{id}">Password</FieldLabel>
            <a href="##" class="ms-auto inline-block text-sm underline">
              Forgot your password?
            </a>
          </div>
          <Input
            id="password-{id}"
            type="password"
            required
            bind:value={password}
          />
        </Field>
        <Field>
          <FieldError errors={error ? [{ message: error }] : []} />
          <Button type="submit" class="w-full" disabled={loading}>
            {loading ? loadingText : buttonText}
          </Button>
        </Field>
      </FieldGroup>
    </form>
  </Card.Content>
</Card.Root>
