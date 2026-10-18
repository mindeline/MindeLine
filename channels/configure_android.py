"""Generate public link configuration only. Does not store keys, build or sign an APK."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


def public_url(value,origin=False):
    p=urlsplit(value)
    if p.scheme!='https' or not p.hostname or not p.hostname.isascii() or p.username or p.password or p.query or p.fragment or p.port not in (None,443):
        raise ValueError('Use a public HTTPS URL without query, credentials or fragment')
    if p.hostname in {'localhost','127.0.0.1'} or p.hostname.endswith('.invalid') or any(c in value for c in '\r\n\\'):
        raise ValueError('Use a real public URL')
    if origin and p.path not in ('','/'):raise ValueError('Gateway must have no path')
    return value.rstrip('/')


def configure(web_url,gateway_url,root):
    web_url=public_url(web_url);gateway_url=public_url(gateway_url,True)
    parsed=urlsplit(web_url)
    # Properties uses ISO-8859-1; encode non-ASCII path characters as Unicode escapes.
    safe_web=''.join(c if ord(c)<128 else '\\u%04x'%ord(c) for c in web_url)
    (root/'mindeline.properties').write_text('webUrl='+safe_web+'\ngatewayHost='+urlsplit(gateway_url).hostname+'\n')
    statements=[{'relation':['delegate_permission/common.handle_all_urls'],
                 'target':{'namespace':'web','site':origin}}
                for origin in dict.fromkeys(['https://'+parsed.netloc,gateway_url])]
    resources=ET.Element('resources')
    ET.SubElement(resources,'string',name='app_name').text='MindeLine'
    # Android string resources require escaping double quotes.
    ET.SubElement(resources,'string',name='asset_statements').text=json.dumps(statements).replace('"','\\"')
    ET.indent(resources)
    ET.ElementTree(resources).write(root/'app/src/main/res/values/strings.xml',encoding='utf-8',xml_declaration=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--web-url',required=True);p.add_argument('--gateway-url',required=True)
    args=p.parse_args()
    configure(args.web_url,args.gateway_url,Path(__file__).resolve().parents[1]/'android')
    print('Public Android links configured. Next: build and sign with Android Studio.')
