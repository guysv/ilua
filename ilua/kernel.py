from ipykernel.kernelbase import Kernel

class ILuaKernel(Kernel):
    implementation = 'ILua'
    implementation_version = '1.0'
    language = "lua"
    lanugae_version = "n/a"
    language_info = {
        'name': 'Lua',
        'mimetype': 'text/plain',
        'file_extension': '.lua'
    }
    banner = "placehoderr.."

    def __init__(self, *args, **kwargs):
        super(*args, **kwargs)

        # Pipe setup

if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=ILuaKernel)
