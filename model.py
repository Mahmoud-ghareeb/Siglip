import torch
import torch.nn as nn
from torch.nn import functional as F
from config import SiglipConfiguration


class SiglipVisionEmbedding(nn.Module):

    def __init__(self, config: SiglipConfiguration):

        super().__init__()

        self.hidden_size = config.hidden_size

        self.patch_embedding = nn.Conv2d(
            in_channels=config.num_channels,
            out_channels=config.hidden_size,
            kernel_size=config.patch_size,
            stride=config.patch_size,
            padding="valid"
        )

        self.num_positions = (config.image_size // config.patch_size) ** 2

        self.position_embeddings = nn.Embedding(
            num_embeddings=self.num_positions, embedding_dim=config.hidden_size)

        self.register_buffer(
            'position_ids',
            torch.arange(0, self.num_positions).expand((1, -1)),
            persistent=False
        )

    def forward(self, pixel_values):

        B, _, _, _ = pixel_values.shape
        # (B, C, H, W) => (B, D, H, W)
        x = self.patch_embedding(pixel_values)
        # (B, D, H, W) => (B, D, L)
        x = x.view(B, self.hidden_size, -1)
        # (B, D, L) => (B, L, D)
        x = x.transpose(-2, -1)
        # (B, L, D) => (B, L, D)
        x += self.position_embeddings(self.position_ids)

        return x


class SiglipAttention(nn.Module):
    def __init__(self, config: SiglipConfiguration):
        super().__init__()

        self.q = nn.Linear(in_features=config.hidden_size,
                           out_features=config.hidden_size, bias=False)
        self.k = nn.Linear(in_features=config.hidden_size,
                           out_features=config.hidden_size, bias=False)
        self.v = nn.Linear(in_features=config.hidden_size,
                           out_features=config.hidden_size, bias=False)

        self.dk = (config.hidden_size // config.num_atttention_heads) ** -0.5

    def forward(self, x):

        B, L, D = x.shape
        print(x.shape)

        # (B, L, D) => (B, H, L, K)
        Q = self.q(x).view(
            B, L, config.num_atttention_heads, -1).transpose(1, 2)
        # (B, L, D) => (B, H, L, K)
        K = self.k(x).view(
            B, L, config.num_atttention_heads, -1).transpose(1, 2)
        # (B, L, D) => (B, H, L, K)
        V = self.v(x).view(
            B, L, config.num_atttention_heads, -1).transpose(1, 2)

        similarty = Q @ K.transpose(-2, -1) * self.dk
        W = F.softmax(similarty, dim=-1)

        x = W @ V

        print(x.shape)
        x = x.transpose(1, 2).contiguous().view(B, L, D)
        print(x.shape)
        return x


class SiglipEncoder(nn.Module):
    def __init__(self, config: SiglipConfiguration):
        super().__init__()

        self.l1 = nn.Sequential(
            nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps),
            SiglipAttention(config)
        )

        # self.l2 = nn.ModuleList([
        #     nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps),
        #     nn.Linear(in_features=config.hidden_size,
        #               out_features=config.intermediate_size),
        #     nn.GELU(approximate="tanh"),
        #     nn.Linear(in_features=config.intermediate_size,
        #               out_features=config.hidden_size)
        # ])

    def forward(self, x):

        x += self.l1(x)
        # x += self.l2(x)

        return x


class SiglipTransformer(nn.Module):
    def __init__(self, config: SiglipConfiguration):
        super().__init__()

        self.embed = SiglipVisionEmbedding(config)
        self.encoder = SiglipEncoder(config)
        self.layer_norm = nn.LayerNorm(
            config.hidden_size, eps=config.layer_norm_eps)

    def forward(self, pixel_values):

        x = self.embed(pixel_values)
        x = self.encoder(x)
        x = self.layer_norm(x)

        return x


class SiglipModel(nn.Module):
    def __init__(self, config: SiglipConfiguration):
        super().__init__()

        self.config = config
        self.vision_model = SiglipTransformer(config)

    def forward(self, pixel_values):

        # (B, C, H, W) -> (B, N, E)
        return self.vision_model(pixel_values)


if __name__ == "__main__":

    x = torch.empty((16, 3, 224, 224), dtype=torch.int32)
    x = x.float()
    config = SiglipConfiguration()

    SiglipModel(config)(x)
