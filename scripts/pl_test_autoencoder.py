import hydra
from rich.logging import RichHandler
from torch.utils.data import DataLoader

# from datasets.med_3Ddataset import ImageDataset

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from dataset.monai_nii_dataset import prepare_dataset
from dataset.med_3Ddataset import ImageDataset
import lightning as pl
from ldm.autoencoderkl.autoencoder import AutoencoderKL
from lightning.pytorch.callbacks import ModelCheckpoint
from dataset.monai_nii_dataset import prepare_dataset
from dataset.monai_nii_dataset1 import AlignDataSet
from lightning.pytorch.strategies import DDPStrategy


@hydra.main(config_path="../conf", config_name="config")
def train(config):
    config = config["config"]

    # * dataset and dataloader
    # test_dl = prepare_dataset(data_path=config.data_path, resize_size=config.resize_size, split="test")
    # val_dataset = ImageDataset(config, split="val")
    # val_dataloader = DataLoader(
    #     dataset=val_dataset,
    #     shuffle=False,
    #     pin_memory=True,
    #     drop_last=True,
    #     num_workers=config.num_workers,
    #     batch_size=config.batch_size,
    # )
    test_ds = AlignDataSet(config, split = "test")
    test_dl = DataLoader(
        dataset=test_ds,
        shuffle=False,
        pin_memory=True,
        drop_last=True,
        num_workers=config.num_workers,
        batch_size=1,
    )

    # * model
    model = AutoencoderKL(save_path=config.hydra_path, **config["model"])
    model.init_from_ckpt("path"
    )

    # * test model
    # config["trainer"].devices = 1
    trainer = pl.Trainer(**config["trainer"])
    trainer.test(model=model, dataloaders=test_dl)


if __name__ == "__main__":
    train()
