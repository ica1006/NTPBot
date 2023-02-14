import datetime
from proxmoxer import ProxmoxAPI
from clients.telegram_client import telegramClient
from config import config
from libraries.utils import bytesConversor, percentToEmoji

class ProxmoxClient():
    def pmxVmStatus(self):
        proxmox = ProxmoxAPI(config.pmx_host, user=config.pmx_user, password=config.pmx_pass, verify_ssl=False)
        for vm in config.vms:
            message = ''
            global_status = proxmox.nodes('pve').qemu(vm).get('status/current')
            status = global_status['status']
            if status == 'running':
                status += ' ✅'
            else:
                status += ' ❌'

            if status == 'running ✅':
                actual_status = proxmox.nodes('pve').qemu(vm).get('rrddata?timeframe=hour')[0]
                cpu = actual_status['cpu'] * 100

                used_mem = bytesConversor(actual_status['mem'])
                max_mem = bytesConversor(actual_status['maxmem'])
                used_mem_p = actual_status['mem'] / actual_status['maxmem'] * 100
                
                uptime = str(datetime.timedelta(seconds=global_status['uptime']))
                disk_space = bytesConversor(global_status['maxdisk'])

                disk_wr = '{}/s'.format(bytesConversor(actual_status['diskwrite']))
                disk_rd = '{}/s'.format(bytesConversor(actual_status['diskread']))

                net_in = '{}/s'.format(bytesConversor(actual_status['netin']))
                net_out = '{}/s'.format(bytesConversor(actual_status['netout']))

                cpu_emoji = percentToEmoji(cpu)
                ram_emoji = percentToEmoji(used_mem_p)

                message += '{} 💻\n'.format(global_status['name'])
                message += 'Status: {}\n'.format(status)
                message += 'CPU: {:.2f}% {}\n'.format(cpu, cpu_emoji)
                message += 'RAM: {}/{}\n          {:.2f}% {}\n'.format(used_mem, max_mem, used_mem_p, ram_emoji)
                message += 'Uptime: {}\n\n'.format(uptime)
                message += 'Boot Drive: {} 💾\n  Write: {}\n  Read: {}\n\n'.format(disk_space, disk_wr, disk_rd)
                message += 'Network 🌐\n  In: {}\n  Out: {}\n\n'.format(net_in, net_out)
            else:
                message += '{} 💻\n'.format(global_status['name'])
                message += 'Status: {}\n'.format(status)
            telegramClient.sendMessage(message)

proxmoxClient = ProxmoxClient()