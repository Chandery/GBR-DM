import numpy as np
from collections import OrderedDict
import torch
import torch.nn as nn
import torch.utils.checkpoint as checkpoint
# from sync_batchnorm import SynchronizedBatchNorm3d
# from torchsummary import summary



class UNet3D(nn.Module):
    def __init__(self, in_channels=1, out_channels=3, init_features=64, use_checkpoint=True):
        """
        Implementations based on the Unet3D paper: https://arxiv.org/abs/1606.06650
        """

        super(UNet3D, self).__init__()

        self.use_checkpoint = use_checkpoint
        features = init_features
        self.encoder1 = UNet3D._block(in_channels, features, name="enc1")
        self.pool1 = nn.MaxPool3d(kernel_size=2, stride=2)
        self.encoder2 = UNet3D._block(features, features * 2, name="enc2")
        self.pool2 = nn.MaxPool3d(kernel_size=2, stride=2)
        self.encoder3 = UNet3D._block(features * 2, features * 4, name="enc3")
        self.pool3 = nn.MaxPool3d(kernel_size=2, stride=2)
        self.encoder4 = UNet3D._block(features * 4, features * 8, name="enc4")
        self.pool4 = nn.MaxPool3d(kernel_size=2, stride=2)

        self.bottleneck = UNet3D._block(features * 8, features * 16, name="bottleneck")

        self.upconv4 = nn.ConvTranspose3d(
            features * 16, features * 8, kernel_size=2, stride=2
        )
        self.decoder4 = UNet3D._block((features * 8) * 2, features * 8, name="dec4")
        self.upconv3 = nn.ConvTranspose3d(
            features * 8, features * 4, kernel_size=2, stride=2
        )
        self.decoder3 = UNet3D._block((features * 4) * 2, features * 4, name="dec3")
        self.upconv2 = nn.ConvTranspose3d(
            features * 4, features * 2, kernel_size=2, stride=2
        )
        self.decoder2 = UNet3D._block((features * 2) * 2, features * 2, name="dec2")
        self.upconv1 = nn.ConvTranspose3d(
            features * 2, features, kernel_size=2, stride=2
        )
        self.decoder1 = UNet3D._block(features * 2, features, name="dec1")

        self.conv = nn.Conv3d(
            in_channels=features, out_channels=out_channels, kernel_size=1
        )

        # ? 这个pre_proj是把(512，16，16，16)降维到(16，16，16，16)
        self.pre_proj = nn.Sequential(
            nn.Conv3d(in_channels=features*8, out_channels=features*2, kernel_size=1),
            nn.BatchNorm3d(num_features=features*2),
            nn.ReLU(inplace=False), # ? 这里不能是True，否则原来的值被直接修改而不是创建新的张量，这样后续调用会出错
            nn.Conv3d(in_channels=features*2, out_channels=features // 2, kernel_size=1),
            nn.BatchNorm3d(num_features=features // 2),
            nn.ReLU(inplace=False),
            nn.Conv3d(in_channels=features // 2, out_channels=16, kernel_size=1),
        )


    def _forward(self, x):
        enc1 = self.encoder1(x)
        enc2 = self.encoder2(self.pool1(enc1))
        enc3 = self.encoder3(self.pool2(enc2))
        enc4 = self.encoder4(self.pool3(enc3))
        bottleneck = self.bottleneck(self.pool4(enc4))

        dec4 = self.upconv4(bottleneck)
        dec4 = torch.cat((dec4, enc4), dim=1)
        dec4 = self.decoder4(dec4)
        
        dec3 = self.upconv3(dec4)
        dec3 = torch.cat((dec3, enc3), dim=1)
        dec3 = self.decoder3(dec3)
        
        dec2 = self.upconv2(dec3)
        dec2 = torch.cat((dec2, enc2), dim=1)
        dec2 = self.decoder2(dec2)
        
        dec1 = self.upconv1(dec2)
        dec1 = torch.cat((dec1, enc1), dim=1)
        dec1 = self.decoder1(dec1)
        
        rec_out = self.conv(dec1)
        c = self.pre_proj(dec4)

        return c, rec_out

    def forward(self, x):
        if self.use_checkpoint:
            return checkpoint.checkpoint(self._forward, x, use_reentrant=False)
        return self._forward(x)

    @staticmethod
    def _block(in_channels, features, name):
        return nn.Sequential(
            OrderedDict(
                [
                    (
                        name + "conv1",
                        nn.Conv3d(
                            in_channels=in_channels,
                            out_channels=features,
                            kernel_size=3,
                            padding=1,
                            bias=True,
                        ),
                    ),
                    (name + "norm1", nn.BatchNorm3d(num_features=features)),
                    (name + "relu1", nn.ReLU(inplace=False)),
                    (
                        name + "conv2",
                        nn.Conv3d(
                            in_channels=features,
                            out_channels=features,
                            kernel_size=3,
                            padding=1,
                            bias=True,
                        ),
                    ),
                    (name + "norm2", nn.BatchNorm3d(num_features=features)),
                    (name + "relu2", nn.ReLU(inplace=False)),
                ]
            )
        )

if __name__ == "__main__":
    unet = UNet3D(in_channels=2, out_channels=1, init_features=64, use_checkpoint=True)
    unet = unet.to("cuda:1")
    unet = unet.train()
    x = torch.randn(1, 2, 128, 128, 128, requires_grad=True).to("cuda:1")
    for i in range(100):
        c, y = unet(x)
    print(c.shape)
    print(y.shape)
