def get_fixed_header():
    return """
metadata = {
    'protocolName': 'Cornucopia Protocol',
    'author': 'Cornucopia <hello@cornucopiabio.com>',
    'source': 'Cornucopia'
}

requirements = {
    "robotType": "Flex",
    "apiLevel": "2.19"
}

def run(protocol):
"""
