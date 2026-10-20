export type DropdownMenuContext = {
  readonly open: boolean;
  setOpen(open: boolean): void;
  toggle(): void;
};

export const DROPDOWN_MENU_CONTEXT = Symbol("hq-dropdown-menu");
