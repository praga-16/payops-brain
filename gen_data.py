"""Deterministic synthetic fixtures. No real people, companies or transactions."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

ROOT = Path(__file__).resolve().parent


def generate(count=30):
    folder = ROOT / 'data' / 'disputes'
    folder.mkdir(parents=True, exist_ok=True)
    scenarios = ['duplicate_debit', 'already_refunded', 'amount_mismatch',
                 'outside_window', 'failed_but_debited', 'unknown_txn', 'clean']
    actions = ['REFUND', 'NO_ACTION', 'ESCALATE', 'ESCALATE', 'REFUND', 'ESCALATE', 'NO_ACTION']
    ledger, disputes = [], []
    try:
        font = ImageFont.truetype('arial.ttf', 25)
    except OSError:
        font = ImageFont.load_default(size=25)
    for i in range(1, count + 1):
        slot = (i - 1) % 7
        scenario = scenarios[slot]
        did, tid = f'D{i:03}', f'SYN-TXN-{i:04}'
        amount = 1250 + i * 37
        day = '2026-06-01' if scenario == 'outside_window' else '2026-11-01'
        fields = dict(transaction_id=tid, amount=str(amount), date=day,
                      reason=scenario.replace('_', ' '), customer_name=f'Synthetic Person {i:02}',
                      phone=f'00000{i:05}', card=f'0000 0000 0000 {i:04}', upi_id=f'person{i}@synthetic')
        if scenario != 'unknown_txn':
            status = 'REFUNDED' if slot == 1 else 'FAILED_DEBITED' if slot == 4 else 'SETTLED'
            ledger.append(dict(id=f'L{i:03}A', transaction_id=tid, amount=str(amount + (50 if slot == 2 else 0)),
                               date=day, status=status, rail=['UPI', 'CARD', 'BIN'][i % 3],
                               customer_name=fields['customer_name'], phone=fields['phone'],
                               card=fields['card'], upi_id=fields['upi_id']))
            if slot == 0:
                ledger.append({**ledger[-1], 'id': f'L{i:03}B'})
        noise = ['rotated', 'blurred', 'low_contrast', 'clean'][(i - 1) % 4]
        fixture = {'fields': fields, 'expected_action': actions[slot], 'scenario': scenario, 'image_variant': noise}
        (folder / f'{did}.json').write_text(json.dumps(fixture, indent=2), encoding='utf-8')
        image = Image.new('RGB', (1000, 680), '#f3f1e9')
        draw = ImageDraw.Draw(image)
        lines = ['SYNTHETIC DISPUTE NOTICE', 'Training fixture / no real payment', '',
                 f'Case: {did}   |   {fields["reason"].upper()}',
                 f'Transaction: {tid}', f'Amount: INR {amount:.2f}', f'Date: {day}',
                 f'Customer: {fields["customer_name"]}', f'Phone: {fields["phone"]}',
                 f'Card: {fields["card"]}', f'UPI: {fields["upi_id"]}']
        for n, line in enumerate(lines):
            draw.text((48, 40 + n * 50), line, font=font, fill='#243640')
        if noise == 'rotated':
            image = image.rotate(2.5, resample=Image.Resampling.BICUBIC, fillcolor='#deded2')
        elif noise == 'blurred':
            image = image.filter(ImageFilter.GaussianBlur(1.2))
        elif noise == 'low_contrast':
            image = ImageEnhance.Contrast(image).enhance(0.35)
        image.save(folder / f'{did}.png')
        disputes.append(dict(id=did, title=fields['reason'].title(), rail=['UPI', 'CARD', 'BIN'][i % 3],
                             amount=str(amount), received_date='2026-11-04', image=f'/notices/{did}.png'))
    (ROOT / 'data' / 'ledger.json').write_text(json.dumps(ledger, indent=2), encoding='utf-8')
    (ROOT / 'data' / 'disputes.json').write_text(json.dumps(disputes, indent=2), encoding='utf-8')
    print(f'Generated {count} synthetic notices and {len(ledger)} ledger records')


if __name__ == '__main__':
    generate()
