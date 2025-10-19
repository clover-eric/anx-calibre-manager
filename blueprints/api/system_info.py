import platform
import subprocess
import os
from flask import Blueprint, jsonify, g
from utils.decorators import login_required_api

system_info_bp = Blueprint('system_info', __name__, url_prefix='/api/system')

@system_info_bp.route('/info', methods=['GET'])
@login_required_api
def get_system_info():
    """Get server system information for bug reports"""
    try:
        # Get OS information
        os_name = platform.system()
        os_release = platform.release()
        os_version = platform.version()
        
        # Try to get more specific Linux distribution info
        distro_info = "Unknown"
        if os_name == "Linux":
            try:
                # Try reading /etc/os-release
                if os.path.exists('/etc/os-release'):
                    with open('/etc/os-release', 'r') as f:
                        lines = f.readlines()
                        for line in lines:
                            if line.startswith('PRETTY_NAME='):
                                distro_info = line.split('=')[1].strip().strip('"')
                                break
            except:
                pass
        
        # Get architecture
        machine = platform.machine()
        arch_map = {
            'x86_64': 'x64 (AMD64/x86_64)',
            'amd64': 'x64 (AMD64/x86_64)',
            'aarch64': 'ARM64 (aarch64/ARMv8)',
            'arm64': 'ARM64 (aarch64/ARMv8)',
            'armv7l': 'ARM32 (ARMv7)',
        }
        architecture = arch_map.get(machine.lower(), machine)
        
        # Get container logs from log files
        container_logs = ""
        try:
            # Check if running in Docker by looking for /.dockerenv
            if os.path.exists('/.dockerenv'):
                hostname = platform.node()
                
                # Read from configured log directory
                log_dir = os.environ.get('LOG_DIR', '/config/logs')
                log_files = [
                    os.path.join(log_dir, 'app.log'),
                    os.path.join(log_dir, 'gunicorn-error.log'),
                    os.path.join(log_dir, 'gunicorn-access.log'),
                ]
                
                log_content_parts = []
                for log_file in log_files:
                    if os.path.exists(log_file):
                        try:
                            result = subprocess.run(
                                ['tail', '-n', '500', log_file],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            if result.returncode == 0 and result.stdout:
                                log_name = os.path.basename(log_file)
                                log_content_parts.append(f"=== {log_name} (last 500 lines) ===\n")
                                log_content_parts.append(result.stdout)
                                log_content_parts.append("\n\n")
                        except:
                            continue
                
                if log_content_parts:
                    container_logs = ''.join(log_content_parts)
                else:
                    container_logs = f"Unable to retrieve container logs. Container hostname: {hostname}\nLog files checked: {', '.join(log_files)}\nPlease use: docker logs {hostname}"
            else:
                container_logs = "Not running in a Docker container"
        except Exception as e:
            container_logs = f"Error retrieving logs: {str(e)}"
        
        return jsonify({
            'os': distro_info if distro_info != "Unknown" else f"{os_name} {os_release}",
            'architecture': architecture,
            'container_logs': container_logs,
            'platform_details': {
                'system': os_name,
                'release': os_release,
                'version': os_version,
                'machine': machine,
                'distro': distro_info
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500