import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = path => readFileSync(new URL('../'+path,import.meta.url),'utf8');
const nav=read('src/WorkspaceNavigation.jsx');
const app=read('src/App.jsx');
const css=read('src/workspace.css');
const refined=read('src/dashboard-polish.css');

test('landlord and tenant navigation uses compact grouped links, preserving original URLs',()=>{
  assert.ok(nav.includes('export const COMPACT_GROUPS'));
  assert.ok(nav.includes('export const TENANT_GROUPS'));
  assert.ok(nav.includes('export function compactGroups'));
  assert.ok(nav.includes('export function WorkspaceSectionTabs'));
  assert.ok(nav.includes("to={'/'+group.pages[0]}"));
  assert.ok(nav.includes("to={'/'+page}"));
  assert.ok(nav.includes("group.pages.includes(active)"));
  assert.ok(nav.includes("role === 'TENANT' ? TENANT_GROUPS : COMPACT_GROUPS"));
  assert.ok(app.includes('<WorkspaceSectionTabs pages={nav} active={page} role={user.role}/>'));
  assert.ok(app.includes('viewResource && nav.includes(page)'));
  for(const key of ['properties','buildings','floors','rooms','tenants','leases','invoices',
    'payments','maintenance','work-orders','reports','security','notifications']){
    assert.ok(nav.includes("'"+key+"'"),key);
  }
});

test('compact sidebar has no normal overflow and tabs are responsive',()=>{
  assert.ok(refined.includes('.portal .workspace-links.kats-nav-accordion'));
  assert.ok(refined.includes('overflow-y:auto'), 'long expanded groups scroll rather than clip');
  assert.ok(nav.includes('kats-nav-group-toggle'), 'related destinations collapse');
  assert.ok(nav.includes('kats-nav-eyebrow'), 'navigation groups have labeled hierarchy');
  assert.ok(nav.includes('aria-expanded={isExpanded}'));
  assert.ok(nav.includes('surface+\'-nav-\''), 'mobile/desktop accordion DOM IDs do not collide');
  assert.ok(css.includes('.portal .kats-section-tabs-list'));
  assert.ok(css.includes('flex-wrap:wrap'));
  assert.ok(css.includes('.portal .kats-section-tab.is-active'));
  assert.ok(css.includes('@media(max-width:640px)'));
});
