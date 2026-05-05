import torch
# Total memory PyTorch thinks it has access to
total_mem = torch.cuda.get_device_properties(0).total_memory
print(f"Total GPU Memory: {total_mem / 1e9:.2f} GB")

