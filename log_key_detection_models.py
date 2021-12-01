# -*- coding: utf-8 -*-

import os
import sys
import time

import torch
import torch.nn as nn
import torch.optim as optim
import pytorch_lightning as pl
import torch.nn.functional as F
from tqdm import tqdm
from torch.utils.data import TensorDataset, DataLoader
from pytorch_lightning.callbacks import EarlyStopping, ModelCheckpoint
from pytorch_lightning.loggers import TensorBoardLogger

# 모델(pytorch lightning)
class DeepLog(pl.LightningModule):
    """Log Anomaly Detection Model

    :param input_size: input data size
    :param hidden_size: lstm hidden size
    :param window_size: past information to help predict the next log key
    :param num_layers: number of lstm layer
    :param num_classes: number of log keys

    :param lr: learning rate
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def __init__(
            self,
            input_size: int,
            hidden_size: int,
            window_size: int,
            num_layers: int,
            num_classes: int,
            lr: float,
    ):
        super(DeepLog, self).__init__()
        self.save_hyperparameters()

        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, num_classes)

        self.criterion = nn.CrossEntropyLoss()

    def forward(self, x):
        h0 = torch.zeros(
            self.hparams.num_layers, x.size(0), self.hparams.hidden_size
        ).to(self.device)
        c0 = torch.zeros(
            self.hparams.num_layers, x.size(0), self.hparams.hidden_size
        ).to(self.device)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out
    # optimizer + scheduler
    def configure_optimizers(self):
        return optim.Adam(self.parameters(), lr=self.hparams.lr)
    # body of training loop (return the val_loss)
    def training_step(self, batch, batch_idx):
        seq, label = batch
        seq = (
            seq.clone()
                .detach()
                .view(-1, self.hparams.window_size, self.hparams.input_size)
                .to(self.device)
        )

        output = self(seq)
        loss = self.criterion(output, label)
        return {"loss": loss}

    # execute every epoch
    def training_epoch_end(self, outputs):
        train_loss_mean = torch.stack([x["loss"] for x in outputs]).mean()
        self.log("trn_loss", train_loss_mean)

    # create valid function to get val_loss
    def validation_step(self, batch, batch_idx):
        seq, label = batch
        seq = (
            seq.clone()
                .detach()
                .view(-1, self.hparams.window_size, self.hparams.input_size)
                .to(self.device)
        )
        output = self(seq)
        loss = self.criterion(output, label)
        return {"vloss": loss}

    # execute every epoch
    def validation_epoch_end(self, outputs):
        valid_loss_mean = torch.stack([x["vloss"] for x in outputs]).mean()
        self.log("val_loss", valid_loss_mean)

