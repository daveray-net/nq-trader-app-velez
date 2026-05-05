import torch
is_available = torch.cuda.is_available()
print(f'ROCm/GPU available: {is_available}')
if is_available:
    print(f'Device Name: {torch.cuda.get_device_name(0)}')
    x = torch.rand(2, 2).to('cuda')
    y = torch.rand(2, 2).to('cuda')
    z = torch.matmul(x, y)
    print('Successfully performed matrix multiplication on Vega 8!')
    print(z)
else:
    print('ROCm not detected. Check HSA_OVERRIDE_GFX_VERSION and driver pass-through.')