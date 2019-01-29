## Import Python libraries ##
import datetime
import re
import xml.etree.ElementTree as ET

## Initiate variables ##
deals = []

## Initiate a Message node ##
msg = ET.Element('Message')
msg.text = '\n'
tree = ET.ElementTree(msg)

## Save current trading day's log file as XML ##
filename = 'LBN_' + str(datetime.datetime.now().strftime('%Y%m%d'))
with open(filename + '.log', 'r') as logFile:
    lines = logFile.readlines()
    for line in lines:   
        if re.search(r'<gid_message type="DO1">', line):
            deals.append(re.search(r'<data.*\/data>', line).group())
            #deals += '\n' + re.search(r'<data.*\/data>', line).group() 

fragment = '\n'.join([deal for deal in deals])
deal = ET.fromstring('<root>' + fragment + '</root>')
msg.append(deal)
tree.write('output.xml')


"""
https://pypi.org/project/auto-py-to-exe/#files
<log><timestamp>2019/01/29 04:18:35.834 GMT</timestamp><RX msg_id="146"><gid_message type="DO1"><header><source>GID</source><target>DOS*</target><parameters><recipient>fxt_MHCV_TOF_LBN</recipient></parameters></header><data><deal_notification type="N"></deal_notification></data></gid_message></RX></log>
"""
