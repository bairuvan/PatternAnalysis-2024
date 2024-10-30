# containing the source code for training, validating, testing and saving your model. 
# The model should be imported from “modules.py” and the data loader should be imported from “dataset.py”. 
# Make sure to plot the losses and metrics during training

import os
import torch
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import DataLoader
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt
from modules import VQVAE  # Import your VQVAE model
from dataset import MedicalImageDataset, get_dataloaders  # Import your dataset classes
from torchmetrics.image import StructuralSimilarityIndexMeasure  # Import SSIM metric

# Set the device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Hyperparameters
num_epochs = 100
batch_size = 16
learning_rate = 1e-4
num_embeddings = 512  # Number of embeddings in vector quantizer
embedding_dim = 64  # Dimensionality of embedding
commitment_cost = 0.25  # Commitment cost
num_res_layers = 2  # Number of residual layers
hidden_channels = 64  # Hidden dimension of the VQVAE

# Data directories
#train_dir = "/Users/bairuan/Documents/uqsem8/comp3710/report/cloned/PatternAnalysis-2024/recognition/VQVAE_Bairu/HipMRI_study_keras_slices_data/keras_slices_train"
#val_dir = "/Users/bairuan/Documents/uqsem8/comp3710/report/cloned/PatternAnalysis-2024/recognition/VQVAE_Bairu/HipMRI_study_keras_slices_data/keras_slices_validate"
#test_dir = "/Users/bairuan/Documents/uqsem8/comp3710/report/cloned/PatternAnalysis-2024/recognition/VQVAE_Bairu/HipMRI_study_keras_slices_data/keras_slices_test"

train_dir = "/home/groups/comp3710/HipMRI_Study_open/keras_slices_data/keras_slices_train"
val_dir = "/home/groups/comp3710/HipMRI_Study_open/keras_slices_data/keras_slices_validate"
test_dir = "/home/groups/comp3710/HipMRI_Study_open/keras_slices_data/keras_slices_test"


def loss_fn(reconstructed, original, quantization_loss):
    """Calculate total loss."""
    recon_loss = F.mse_loss(reconstructed, original)
    total_loss = recon_loss + quantization_loss
    return total_loss


def plot_losses_and_ssim(train_losses, val_losses, train_ssims, val_ssims):
    """Plot training and validation losses and SSIM."""
    fig, ax1 = plt.subplots(figsize=(10, 5))

    # Plot losses
    ax1.set_xlabel('Epochs')
    ax1.set_ylabel('Loss', color='blue')
    ax1.plot(train_losses, label='Training Loss', color='blue')
    ax1.plot(val_losses, label='Validation Loss', color='orange')
    ax1.tick_params(axis='y', labelcolor='blue')
    ax1.legend(loc='upper left')

    # Create a second y-axis for SSIM
    ax2 = ax1.twinx()
    ax2.set_ylabel('SSIM', color='green')
    ax2.plot(train_ssims, label='Training SSIM', color='green', linestyle='--')
    ax2.plot(val_ssims, label='Validation SSIM', color='red', linestyle='--')
    ax2.tick_params(axis='y', labelcolor='green')
    ax2.legend(loc='upper right')

    plt.title('Training and Validation Loss & SSIM')
    plt.grid()
    plt.savefig('loss_ssim_plot.png')
    plt.show()


if __name__ == '__main__':
    # Create data loaders
    train_loader, val_loader, test_loader = get_dataloaders(train_dir, val_dir, test_dir, batch_size=batch_size)

    # Initialize the model
    model = VQVAE(1, hidden_channels, num_embeddings, embedding_dim, num_res_layers).to(device)
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    train_losses = []
    val_losses = []
    train_ssims = []
    val_ssims = []
    
    # Initialize SSIM metric
    ssim_metric = StructuralSimilarityIndexMeasure(data_range=1.0).to(device)

    # Training loop
    for epoch in range(num_epochs):
        model.train()  # Set the model to training mode
        train_loss = 0
        train_ssim = 0

        for batch in tqdm(train_loader):
            optimizer.zero_grad()
            batch = batch.to(device)

            # Forward pass
            reconstructed, quantization_loss = model(batch)

            # Calculate loss
            loss = loss_fn(reconstructed, batch, quantization_loss)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            train_ssim += ssim_metric(reconstructed, batch).item()

        avg_train_loss = train_loss / len(train_loader)
        avg_train_ssim = train_ssim / len(train_loader)
        train_losses.append(avg_train_loss)
        train_ssims.append(avg_train_ssim)
        print(f"Epoch [{epoch + 1}/{num_epochs}], Average Training Loss: {avg_train_loss:.4f}, Average Training SSIM: {avg_train_ssim:.4f}")

        # Validation loop
        model.eval()  # Set the model to evaluation mode
        val_loss = 0
        val_ssim = 0
        with torch.no_grad():
            for batch in val_loader:
                batch = batch.to(device)
                reconstructed, quantization_loss = model(batch)
                loss = loss_fn(reconstructed, batch, quantization_loss)
                val_loss += loss.item()
                val_ssim += ssim_metric(reconstructed, batch).item()

        avg_val_loss = val_loss / len(val_loader)
        avg_val_ssim = val_ssim / len(val_loader)
        val_losses.append(avg_val_loss)
        val_ssims.append(avg_val_ssim)
        print(f"Epoch [{epoch + 1}/{num_epochs}], Average Validation Loss: {avg_val_loss:.4f}, Average Validation SSIM: {avg_val_ssim:.4f}")

        # Save the model at the end of training
        if (epoch + 1) % 10 == 0:  # Save every 10 epochs
            torch.save(model.state_dict(), f'vqvae_model_epoch_{epoch + 1}.pth')
            print(f"Model saved at epoch {epoch + 1}.")

    # Final model save
    torch.save(model.state_dict(), 'vqvae_final_model.pth')
    print("Final model saved.")

    # Plot the losses and SSIM
    plot_losses_and_ssim(train_losses, val_losses, train_ssims, val_ssims)
