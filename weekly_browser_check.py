"""Browser journey/layout check for synthetic local Weekly QA; no live service."""
from playwright.sync_api import sync_playwright
import json
import argparse
from pathlib import Path
parser=argparse.ArgumentParser(description='Local Weekly browser QA; requires running qa_weekly_app.py')
parser.add_argument('--url',default='http://127.0.0.1:8511')
parser.add_argument('--chromium',default=None,help='Optional installed Chromium executable')
parser.add_argument('--output',default='weekly-mobile-qa')
args=parser.parse_args()
out=Path(args.output).resolve()
out.mkdir(parents=True,exist_ok=True)
checks=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=args.chromium,headless=True,chromium_sandbox=True)
    page=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True)
    page.set_default_timeout(60000)
    page.goto(args.url)
    page.get_by_role('button',name='Start Official Game',exact=True).wait_for(timeout=45000)
    def check(label):
        page.screenshot(path=str(out/(label+'.png')),full_page=True)
        dimensions=page.evaluate('''() => ({viewport:innerWidth,document:document.documentElement.scrollWidth,body:document.body.scrollWidth,main:[...document.querySelectorAll('[data-testid=stMain]')].map(e=>({client:e.clientWidth,scroll:e.scrollWidth}))})''')
        assert dimensions['document']<=dimensions['viewport'],(label,dimensions)
        assert dimensions['body']<=dimensions['viewport'],(label,dimensions)
        assert all(m['scroll']<=m['client'] for m in dimensions['main']),(label,dimensions)
        checks.append({'screen':label,**dimensions})
    check('intro-390')
    assert 'Bob' not in page.inner_text('body')
    page.get_by_role('button',name='Start Official Game',exact=True).click()
    page.get_by_role('heading',name='Round 1 of 13 · Roll 1 of 3').wait_for()
    check('play-390')
    dice=page.locator('.st-key-weekly_dice button:visible')
    dice.nth(4).wait_for()
    boxes=[dice.nth(i).bounding_box() for i in range(5)]
    assert all(b['width']>=44 and b['height']>=44 for b in boxes),boxes
    assert max(b['y'] for b in boxes)-min(b['y'] for b in boxes)<2,boxes
    dice.nth(1).click()
    page.get_by_text('Held: none',exact=True).wait_for(state='hidden')
    page.get_by_role('button',name='Roll remaining dice',exact=True).click()
    page.get_by_role('heading',name='Round 1 of 13 · Roll 2 of 3').wait_for()
    for width in [320,430,1280]:
        page.set_viewport_size({'width':width,'height':900})
        check('play-'+str(width))
        boxes=[dice.nth(i).bounding_box() for i in range(5)]
        assert all(b and b['width']>=44 and b['height']>=44 for b in boxes),boxes
        assert max(b['y'] for b in boxes)-min(b['y'] for b in boxes)<2,boxes
        checks.append({'dice_width':width,'boxes':boxes})
    page.set_viewport_size({'width':390,'height':844})
    page.get_by_text('Your scorecard',exact=True).click()
    table=page.locator('table.weekly-scorecard:visible').first
    table.wait_for()
    page.wait_for_function('''() => {const t=document.querySelector('details[open] table.weekly-scorecard');return t && t.closest('details').getBoundingClientRect().bottom>=t.getBoundingClientRect().bottom;}''')
    assert table.locator('tbody tr').count()==13
    table.screenshot(path=str(out/'scorecard-table-390.png'))
    check('scorecard-390')
    page.get_by_text('Your scorecard',exact=True).click()
    for r in range(1,14):
        box=page.get_by_role('combobox',name='Scoring category',exact=True)
        page.locator('[data-testid=stApp][data-test-script-state=notRunning]').wait_for()
        box.press('ArrowDown')
        page.get_by_role('option').first.press('Enter')
        page.locator('[data-testid=stApp][data-test-script-state=notRunning]').wait_for()
        page.get_by_role('button',name='Score this round',exact=True).click()
        if r<13:
            page.get_by_role('heading',name=f'Round {r+1} of 13 · Roll 1 of 3').wait_for()
        else:
            page.get_by_text('Official Score (locked):',exact=False).wait_for()
    check('complete-390')
    assert 'Bob' in page.inner_text('body')
    official=page.get_by_text('Official Score (locked):',exact=False).inner_text()
    page.get_by_text('Review your rounds',exact=True).click()
    page.get_by_text('Round 13 ·',exact=False).wait_for()
    page.get_by_text('Round 1 ·',exact=False).scroll_into_view_if_needed()
    check('review-top-390')
    page.get_by_text('Round 13 ·',exact=False).scroll_into_view_if_needed()
    check('review-bottom-390')
    page.get_by_text('Review your rounds',exact=True).click()
    page.get_by_role('button',name="Replay This Week's Dice",exact=True).click()
    page.get_by_text('Practice — does not affect standings',exact=True).wait_for()
    page.get_by_role('heading',name='Round 1 of 13 · Roll 1 of 3').wait_for()
    check('replay-390')
    page.get_by_role('button',name='Refresh saved game',exact=True).click()
    page.get_by_role('heading',name='Round 1 of 13 · Roll 1 of 3').wait_for()
    for r in range(1,14):
        page.locator('[data-testid=stApp][data-test-script-state=notRunning]').wait_for()
        page.get_by_role('combobox',name='Scoring category',exact=True).press('ArrowDown')
        page.get_by_role('option').first.press('Enter')
        page.locator('[data-testid=stApp][data-test-script-state=notRunning]').wait_for()
        page.get_by_role('button',name='Score this round',exact=True).click()
        if r<13:
            page.get_by_role('heading',name=f'Round {r+1} of 13 · Roll 1 of 3').wait_for()
    page.get_by_role('button',name="Replay This Week's Dice",exact=True).wait_for()
    assert page.get_by_text('Official Score (locked):',exact=False).inner_text()==official
    page.get_by_role('button',name="Replay This Week's Dice",exact=True).scroll_into_view_if_needed()
    check('replay-complete-390')
    checks.append({'replay_complete':True,'official_unchanged':True})
    checks.append({'flow':'start / hold / reroll / 13 scores / standings / replay','passed':True,'physical_device':False})
    browser.close()
(out/'results.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(checks,indent=2))
