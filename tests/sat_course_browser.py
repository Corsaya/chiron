import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
parser = argparse.ArgumentParser(description='Verify the synthetic SAT Classroom preview.')
parser.add_argument('--url', default='http://127.0.0.1:8768')
parser.add_argument('--chromium', default=None)
parser.add_argument('--output', default='/tmp/chiron-sat-verification')
args = parser.parse_args()
out=Path(args.output);out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=args.chromium, headless=True)
 page=browser.new_page(viewport={'width':1280,'height':900}, reduced_motion='reduce')
 errors=[]
 page.on('pageerror',lambda error:errors.append(str(error)))
 page.goto(args.url.rstrip('/') + '/static/classroom.html#/SAT')
 page.get_by_role('heading',name='Next action',exact=True).wait_for()
 page.get_by_text('Why this?',exact=True).click()
 assert page.get_by_text('Two observed errors',exact=False).is_visible()
 assert page.locator('#mark-done').count()==0
 page.screenshot(path=str(out/'sat-desktop.png'),full_page=True)
 page.get_by_role('button',name='a five-question practice block',exact=True).click()
 page.get_by_text('Synthetic exercise.',exact=True).wait_for()
 assert page.locator('#mark-done').count()==0
 page.get_by_role('button',name='Back to SAT plan').click()
 page.get_by_role('heading',name='Next action',exact=True).wait_for()
 page.set_viewport_size({'width':390,'height':844})
 page.get_by_text('Why this?',exact=True).click()
 assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
 page.screenshot(path=str(out/'sat-mobile.png'),full_page=True)
 # Validate disclosure and source controls through keyboard navigation.
 page.get_by_text('Why this?',exact=True).focus()
 page.keyboard.press('Enter')
 assert not page.locator('details').evaluate('(el) => el.open')
 page.keyboard.press('Enter')
 assert page.locator('details').evaluate('(el) => el.open')
 # Empty and failed-source states must remain honest and recoverable.
 page.route('**/api/classrooms/SAT/plan', lambda route: route.fulfill(json={
  'action':None, 'evidence':None, 'source':{'path':'Home.md','modified_at':'unknown','revision':'0'*64},
  'references':[], 'limitations':'No personal evidence is available.'
 }))
 page.reload()
 page.get_by_text('No next action is recorded in the course Home.',exact=True).wait_for()
 page.get_by_text('Why this?',exact=True).click()
 assert page.get_by_text('No supporting evidence section is recorded.',exact=False).is_visible()
 page.unroute('**/api/classrooms/SAT/plan')
 page.route('**/api/classrooms/SAT/plan', lambda route: route.fulfill(status=503,json={'detail':'Synthetic read failure'}))
 page.reload()
 page.get_by_role('button',name='Retry',exact=True).wait_for()
 assert page.locator('.side-item').count()>0
 page.unroute('**/api/classrooms/SAT/plan')
 page.get_by_role('button',name='Retry',exact=True).click()
 page.get_by_role('heading',name='Next action',exact=True).wait_for()
 assert not errors,errors
 browser.close()
print('Browser flow passed: plan, evidence, source opening, return, mobile width, keyboard disclosure, no SAT completion, no JS errors.')
print(out)
