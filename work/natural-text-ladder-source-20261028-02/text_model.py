"""Decoder Transformer for the natural-text ladder: vendor/model.py's Block and Model with the vocabulary as a parameter.

The block, initialization and forward pass are the confirmation's model code unchanged; only VOCAB = 84 became an
argument (default text_plan.VOCAB). Imported only by the Linux worker.
"""
import torch
from torch import nn
from torch.nn import functional as F
import text_plan as plan


class Block(nn.Module):
    def __init__(self, width, heads):
        super().__init__()
        self.heads = heads
        self.ln1, self.ln2 = nn.LayerNorm(width), nn.LayerNorm(width)
        self.qkv = nn.Linear(width, 3 * width)
        self.proj = nn.Linear(width, width)
        self.ff = nn.Sequential(nn.Linear(width, 4 * width), nn.GELU(), nn.Linear(4 * width, width))

    def forward(self, x):
        b, t, c = x.shape
        q, k, v = self.qkv(self.ln1(x)).reshape(b, t, 3, self.heads, c // self.heads).permute(2, 0, 3, 1, 4)
        a = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        x = x + self.proj(a.transpose(1, 2).reshape(b, t, c))
        return x + self.ff(self.ln2(x))


class Model(nn.Module):
    def __init__(self, width, layers, length, vocab=plan.VOCAB):
        super().__init__()
        self.token = nn.Embedding(vocab, width)
        self.position = nn.Embedding(length, width)
        self.blocks = nn.Sequential(*[Block(width, plan.HEADS) for _ in range(layers)])
        self.norm = nn.LayerNorm(width)
        self.head = nn.Linear(width, vocab, bias=False)
        self.apply(self.initialize)

    @staticmethod
    def initialize(module):
        if isinstance(module, (nn.Linear, nn.Embedding)):
            nn.init.normal_(module.weight, std=0.02)
            if isinstance(module, nn.Linear) and module.bias is not None:
                nn.init.zeros_(module.bias)

    def forward(self, x):
        h = self.token(x) + self.position(torch.arange(x.shape[1], device=x.device))[None]
        return self.head(self.norm(self.blocks(h)))
