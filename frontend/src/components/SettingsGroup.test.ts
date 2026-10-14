import { createSSRApp, h } from "vue";
import { renderToString } from "vue/server-renderer";
import { describe, expect, it } from "vitest";
import SettingsGroup from "./SettingsGroup.vue";
import groupSource from "./SettingsGroup.vue?raw";

async function render(props: { id: string; title: string; open: boolean; problem: boolean }): Promise<string> {
  const app = createSSRApp({
    render: () => h(SettingsGroup, props, { default: () => [h("div", { class: "field" }, "one"), h("div", { class: "field" }, "two")] }),
  });
  return renderToString(app);
}

describe("a settings group", () => {
  it("is a details element with the title in its summary, open when it is told to be", async () => {
    const html = await render({ id: "colormap", title: "Colormap", open: true, problem: false });
    expect(html).toMatch(/<details[^>]*\sopen[\s=>]/);
    expect(html).toMatch(/<summary[^>]*>[\s\S]*Colormap[\s\S]*<\/summary>/);
    expect(html).toContain('data-group="colormap"');
  });

  it("has no open attribute when collapsed, and still contains its controls (a collapsed group keeps what is in it)", async () => {
    const html = await render({ id: "colormap", title: "Colormap", open: false, problem: false });
    expect(html).not.toMatch(/<details[^>]*\sopen[\s=>]/);
    expect(html).toContain(">one<");
    expect(html).toContain(">two<");
  });

  it("says in its title that something needs attention only when there is a problem", async () => {
    expect(await render({ id: "analysis", title: "Analysis", open: false, problem: true })).toContain("needs attention");
    expect(await render({ id: "analysis", title: "Analysis", open: false, problem: false })).not.toContain("needs attention");
    expect(await render({ id: "analysis", title: "Analysis", open: true, problem: true })).toContain("needs attention");
  });

  it("puts the controls in a flex body, in the order they were given", async () => {
    const html = await render({ id: "analysis", title: "Analysis", open: true, problem: false });
    expect(html).toMatch(/<div class="settings-group-body"[^>]*>(<!--\[-->)?\s*<div class="field">one<\/div><div class="field">two<\/div>/);
  });
});

describe("the layout of a settings group (source guards: the styles cannot be seen without a browser)", () => {
  const css = groupSource.slice(groupSource.indexOf("<style"));

  it("is a wrapping flex row with the same gap between rows and cells", () => {
    expect(css).toMatch(/\.settings-group-body\s*\{[^}]*display:\s*flex/);
    expect(css).toMatch(/\.settings-group-body\s*\{[^}]*flex-wrap:\s*wrap/);
    expect(css).toMatch(/\.settings-group-body\s*\{[^}]*gap:/);
  });

  it("gives every cell half of the row minus half of the gap, and may shrink", () => {
    const cell = css.match(/\.settings-group-body\s*>\s*\.field\s*\{([^}]*)\}/)?.[1] ?? "";
    expect(cell).toMatch(/flex:\s*1\s+1\s+calc\(50%\s*-\s*var\(--group-gap\)\s*\/\s*2\)/);
    expect(cell).toContain("min-width: 0");
  });

  it("lets the last cell of an odd group take the whole row", () => {
    const last = css.match(/\.settings-group-body\s*>\s*\.field:last-child:nth-child\(odd\)\s*\{([^}]*)\}/)?.[1] ?? "";
    expect(last).toMatch(/flex-basis:\s*100%/);
  });

  it("puts one cell on each row on a very narrow screen", () => {
    const query = css.match(/@media\s*\(max-width:\s*26rem\)\s*\{([\s\S]*?)\}\s*\}/)?.[1] ?? "";
    expect(query).toMatch(/\.settings-group-body\s*>\s*\.field\s*\{[^}]*flex-basis:\s*100%/);
  });

  it("sets the title in the label font and size (Roboto Slab, 0.9 rem) through the shared variables", () => {
    const title = css.match(/\.settings-group-title\s*\{([^}]*)\}/)?.[1] ?? "";
    expect(title).toContain("font-family: var(--label-font)");
    expect(title).toContain("font-size: var(--label-size)");
  });

  it("does not hide the body with v-if or v-show (the native element hides it, so no value is dropped)", () => {
    const template = groupSource.slice(0, groupSource.indexOf("<style"));
    const body = template.match(/<div class="settings-group-body"[^>]*>/)?.[0] ?? "";
    expect(body).not.toMatch(/v-if|v-show/);
    expect(template).toContain("<details");
    expect(template).toContain("<summary");
  });

  it("reports the open state that the browser says, not a toggle (so a second report of the same state changes nothing)", () => {
    expect(groupSource).toMatch(/@toggle=/);
    expect(groupSource).toMatch(/\.open/);
  });
});
