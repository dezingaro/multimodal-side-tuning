"""
Creative Common 4.0 License for reuse with citation
&copy; 2020 Stefano Pio Zingaro
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision

from .utils import merge


class FusionNetConcat(nn.Module):
    def __init__(self, embedding_dim, num_classes,
                 dropout_prob=.2, custom_embedding=False,
                 custom_num_embeddings=0):
        super(FusionNetConcat, self).__init__()
        self.embedding_dim = embedding_dim
        self.num_classes = num_classes
        self.dropout_prob = dropout_prob

        self.base = MobileNet(num_classes=self.num_classes, classify=False)
        for param in self.base.parameters():
            param.requires_grad_(False)
        self.side_image = MobileNet(num_classes=self.num_classes, classify=False)
        self.side_text = ShawnNet(self.embedding_dim,
                                  num_classes=self.num_classes,
                                  windows=[3, 4, 5],
                                  custom_embedding=custom_embedding,
                                  custom_num_embeddings=custom_num_embeddings,
                                  classify=False)

        self.fc1fus = nn.Linear(
            self.side_text.num_filters * len(self.side_text.windows),
            self.base.last_channel)
        self.fc2fus = nn.Linear(
            self.base.last_channel,
            128)

        self.classifier = nn.Sequential(nn.Dropout(self.dropout_prob),
                                        nn.Linear(128*3, self.num_classes))

    def forward(self, y):
        b_x, s_text_x = y[0], y[1]

        s_image_x = b_x.clone()
        s_image_x = self.side_image(s_image_x)
        s_image_x = self.fc2fus(s_image_x)

        b_x = self.base(b_x)
        b_x = self.fc2fus(b_x)

        s_text_x = self.side_text(s_text_x)
        s_text_x = self.fc1fus(s_text_x)
        s_text_x = self.fc2fus(s_text_x)

        x = torch.cat([b_x, s_image_x, s_text_x], 1)
        x = self.classifier(x)

        return x


class FusionSideNetDirect(nn.Module):
    def __init__(self, embedding_dim, num_classes, alphas=None,
                 dropout_prob=.2, custom_embedding=False,
                 custom_num_embeddings=0):
        super(FusionSideNetDirect, self).__init__()
        self.embedding_dim = embedding_dim
        self.num_classes = num_classes
        if alphas is None:
            alphas = [.3, .3]
        self.alphas = alphas
        self.dropout_prob = dropout_prob

        self.base = MobileNet(num_classes=self.num_classes, classify=False)
        for param in self.base.parameters():
            param.requires_grad_(False)
        self.side_image = MobileNet(num_classes=self.num_classes, classify=False)
        self.side_text = ShawnNet(self.embedding_dim,
                                  num_classes=self.num_classes,
                                  windows=[3, 4, 5],
                                  custom_embedding=custom_embedding,
                                  custom_num_embeddings=custom_num_embeddings,
                                  classify=False)

        self.fc1fus = nn.Linear(
            self.side_text.num_filters * len(self.side_text.windows),
            self.base.last_channel)
        self.classifier = nn.Sequential(nn.Dropout(self.dropout_prob),
                                        nn.Linear(self.base.last_channel, self.num_classes))

    def forward(self, y):
        b_x, s_text_x = y[0], y[1]

        s_image_x = b_x.clone()
        s_image_x = self.side_image(s_image_x)

        b_x = self.base(b_x)

        s_text_x = self.side_text(s_text_x)
        s_text_x = self.fc1fus(s_text_x)

        x, d = merge([b_x, s_image_x, s_text_x], self.alphas, return_distance=True)
        x = self.classifier(x)

        return x, d


class FusionSideNetFc(nn.Module):
    def __init__(self, embedding_dim, num_classes, alphas=None,
                 dropout_prob=.2, custom_embedding=False,
                 custom_num_embeddings=0, side_fc=512):
        super(FusionSideNetFc, self).__init__()
        self.embedding_dim = embedding_dim
        self.num_classes = num_classes
        if alphas is None:
            alphas = [.3, .3]
        self.alphas = alphas
        self.dropout_prob = dropout_prob

        self.base = MobileNet(num_classes=self.num_classes, classify=False)
        for param in self.base.parameters():
            param.requires_grad_(False)
        self.side_image = MobileNet(num_classes=self.num_classes, classify=False)
        self.side_text = ShawnNet(self.embedding_dim,
                                  num_classes=self.num_classes,
                                  windows=[3, 4, 5],
                                  custom_embedding=custom_embedding,
                                  custom_num_embeddings=custom_num_embeddings,
                                  classify=False)

        self.fc1fus = nn.Linear(
            self.side_text.num_filters * len(self.side_text.windows),
            self.base.last_channel)
        self.classifier = nn.Sequential(nn.Dropout(self.dropout_prob),
                                        nn.Linear(self.base.last_channel, side_fc),
                                        nn.Dropout(self.dropout_prob),
                                        nn.Linear(side_fc, self.num_classes))

    def forward(self, y):
        b_x, s_text_x = y[0], y[1]

        s_image_x = b_x.clone()
        s_image_x = self.side_image(s_image_x)

        b_x = self.base(b_x)

        s_text_x = self.side_text(s_text_x)
        s_text_x = self.fc1fus(s_text_x)

        x, d = merge([b_x, s_image_x, s_text_x], self.alphas, return_distance=True)
        x = self.classifier(x)

        return x, d


class TextSideNet(nn.Module):
    def __init__(self, embedding_dim, num_classes, alphas=None,
                 dropout_prob=.2, custom_embedding=False,
                 custom_num_embeddings=0):
        super(TextSideNet, self).__init__()
        self.embedding_dim = embedding_dim
        self.num_classes = num_classes
        if alphas is None:
            alphas = [.3]
        self.alphas = alphas
        self.dropout_prob = dropout_prob

        self.base = MobileNet(num_classes=self.num_classes, classify=False)
        for param in self.base.parameters():
            param.requires_grad_(False)
        self.side_text = ShawnNet(self.embedding_dim,
                                  num_classes=self.num_classes,
                                  windows=[3, 4, 5],
                                  custom_embedding=custom_embedding,
                                  custom_num_embeddings=custom_num_embeddings,
                                  classify=False)

        self.fc1fus = nn.Linear(
            self.side_text.num_filters * len(self.side_text.windows),
            self.base.last_channel)
        self.classifier = nn.Sequential(nn.Dropout(self.dropout_prob),
                                        nn.Linear(self.base.last_channel, self.num_classes))

    def forward(self, y):
        b_x, s_text_x = y[0], y[1]

        b_x = self.base(b_x)

        s_text_x = self.side_text(s_text_x)
        s_text_x = self.fc1fus(s_text_x)

        x, d = merge([b_x, s_text_x], self.alphas, return_distance=True)
        x = self.classifier(x)

        return x, d


class MobileNet(nn.Module):
    def __init__(self, num_classes, dropout_prob=.2, classify=True):
        super(MobileNet, self).__init__()
        self.dropout_prob = dropout_prob
        self.model = torchvision.models.mobilenet_v2(pretrained=True)
        self.features = self.model.features
        self.last_channel = self.model.last_channel
        self.classify = classify
        if self.classify:
            self.classifier = nn.Sequential(nn.Dropout(self.dropout_prob),
                                            nn.Linear(self.last_channel,
                                                      num_classes))

    def forward(self, x):
        x = self.features(x)
        x = x.mean([2, 3])
        if self.classify:
            x = self.classifier(x)

        return x


class ShawnNet(nn.Module):
    def __init__(self, embedding_dim, num_filters=512, windows=None,
                 dropout_prob=.2, num_classes=10,
                 custom_embedding=False, custom_num_embeddings=0, classify=True):
        super(ShawnNet, self).__init__()
        self.embedding_dim = embedding_dim
        self.num_filters = num_filters
        if windows is None:
            self.windows = [3, 4, 5]
        else:
            self.windows = windows
        self.dropout_prob = dropout_prob
        self.num_classes = num_classes
        self.custom_embedding = custom_embedding

        if self.custom_embedding:
            self.embedding = nn.Embedding(custom_num_embeddings, self.embedding_dim)
        self.convs = nn.ModuleList([
            nn.Conv2d(1, self.num_filters, (i, self.embedding_dim)) for i in
            self.windows
        ])
        self.classify = classify
        if self.classify:
            self.classifier = nn.Sequential(nn.Dropout(self.dropout_prob),
                                            nn.Linear(len(
                                                self.windows) * self.num_filters,
                                                      self.num_classes))

    def forward(self, x):
        if self.custom_embedding:
            x = self.embedding(x)
        x = x.unsqueeze(1)

        x = [F.relu(conv(x)).squeeze(3) for conv in self.convs]
        x = [F.max_pool1d(i, i.size(2)).squeeze(2) for i in x]
        x = torch.cat(x, 1)

        if self.classify:
            x = self.classifier(x)

        return x
