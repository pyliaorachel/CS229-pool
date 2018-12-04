import torch
import torch.nn as nn
import torch.nn.functional as F

from .utils import set_init


class Net(nn.Module):
    def __init__(self, s_dim, a_dim, h_dim):
        super().__init__()

        self.s_dim = s_dim
        self.a_dim = a_dim

        # Actor
        self.a1 = nn.Linear(s_dim, h_dim)
        self.mu = nn.Linear(h_dim, a_dim)
        self.sigma = nn.Linear(h_dim, a_dim)

        # Critic
        self.c1 = nn.Linear(s_dim, h_dim)
        self.v = nn.Linear(h_dim, 1)

        set_init([self.a1, self.mu, self.sigma, self.c1, self.v])
        self.distribution = torch.distributions.Normal

    def forward(self, x):
        a1 = F.relu(self.a1(x))
        # TODO: not sure if using sigmoid to compress the range is a good idea, since 0 and 1 are unapproachable values
        mu = torch.sigmoid(self.mu(a1)) # both actions in range [0, 1]
        sigma = F.softplus(self.sigma(a1)) + 0.001 # avoid 0

        c1 = F.relu(self.c1(x))
        values = self.v(c1)

        return mu, sigma, values

    def choose_action(self, s, ranges=None):
        self.train(False)
        mu, sigma, _ = self.forward(s)
        m = self.distribution(mu, sigma)
        a = m.sample().numpy()

        # Clip value
        if ranges is not None:
            for i in range(a.size):
                a[i] = a[i].clip(*ranges[i])
        return a

    def loss_func(self, s, a, v_t):
        self.train()
        mu, sigma, values = self.forward(s)
        td = v_t - values
        c_loss = td.pow(2)

        m = self.distribution(mu, sigma)
        log_prob = m.log_prob(a)
        exp_v = log_prob * td.detach()
        a_loss = -exp_v

        entropy = -m.entropy() # for exploration
        total_loss = (a_loss + c_loss + 0.005 * entropy).mean()
        return total_loss
