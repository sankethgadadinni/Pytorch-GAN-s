import os

import torch
import torchvision
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import matplotlib.pyplot as plt
from omegaconf import OmegaConf
from argparse import ArgumentParser


import pytorch_lightning as pl
from pytorch_lightning import loggers as pl_loggers

from generator import Generator
from discriminator import Discriminator
from data import MNISTDataModule


class GAN(pl.LightningModule):
    def __init__(self, config):
        super(GAN, self).__init__()
        
        self.config = config
        
        self.generator = Generator(config=self.config)
        self.discriminator = Discriminator()
        
        #random noise
        self.validation_z = torch.randn(6, self.config.latent_dim)
        
        
    
    def forward(self, z):
        return self.generator(z)
    
    
    def adversarial_loss(self, y_hat, y):
        return F.binary_cross_entropy(y_hat, y)
    
    
    def training_step(self, batch, batch_idx, optimizer_idx):
        real_imgs, _ = batch

        # sample noise
        z = torch.randn(real_imgs.shape[0], self.config.latent_dim)
        z = z.type_as(real_imgs)

        # train generator
        if optimizer_idx == 0:
            fake_imgs = self(z)
            y_hat = self.discriminator(fake_imgs)
            
            y = torch.ones(real_imgs.size(0), 1)
            y = y.type_as(real_imgs)
            
            g_loss = self.adversarial_loss(y_hat,y)
            
            
            log_dict = {"g_loss": g_loss}
            output = {"loss": g_loss, "progress_bar": log_dict, "log": log_dict}
            return output

        

        # train discriminator
        if optimizer_idx == 1:
            
            y_hat_real = self.discriminator(real_imgs)
            y_real = torch.ones(real_imgs.size(0), 1)
            y_real = y_real.type_as(real_imgs)
            
            real_loss = self.adversarial_loss(y_hat_real, y_real)

            y_hat_fake = self.discriminator(self(z).detach())
            y_fake = torch.zeros(real_imgs.size(0), 1)
            y_fake = y_fake.type_as(real_imgs)
            
            fake_loss = self.adversarial_loss(y_hat_fake, y_fake) 


            d_loss = (real_loss + fake_loss) / 2
            log_dict = {"d_loss": d_loss}
            output = {"loss": d_loss, "progress_bar": log_dict, "log": log_dict}
            return output
    
    
    def configure_optimizers(self):
        lr = self.config.lr
        opt_g = torch.optim.Adam(self.generator.parameters(), lr=lr)
        opt_d = torch.optim.Adam(self.discriminator.parameters(), lr=lr)
        
        return [opt_g, opt_d],[]
    
    def plot_imgs(self):
        z = self.validation_z.type_as(self.generator.linear.weight)
        
        sample_imgs = self(z).cpu()
        
        print("Epoch", self.current_epoch)
        
        fig = plt.figure()
        for i in range(sample_imgs.size(0)):
            plt.subplot(2, 3, i+1)
            plt.tight_layout()
            plt.imshow(sample_imgs.detach()[i, 0,:, :], cmap='gray_r', interpolation='none')
            plt.title("Generated Data")
            plt.xticks([])
            plt.yticks([])
            plt.axis('off')
        
        plt.show()
        
    
    def on_epoch_end(self):
        self.plot_imgs()
        
        


if __name__ == '__main__':
    
    parser = ArgumentParser()
    parser.add_argument("-c", "--config", type=str, required=True, help="provide the config file")
    args = parser.parse_args()

    configFile = OmegaConf.load(args.config)
    config = configFile.config

    tb_logger = pl_loggers.TensorBoardLogger('logs/GAN')


    dm = MNISTDataModule(config=config)

    model = GAN(config=config)

    trainer = pl.Trainer(max_epochs=config.epochs,gpus=config.gpus,log_every_n_steps=1, progress_bar_refresh_rate=20,logger=tb_logger)

    trainer.fit(model, dm)
    trainer.test(model, dm)