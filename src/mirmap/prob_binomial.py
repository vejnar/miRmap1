# -*- coding: utf-8 -*-

#
# Copyright © 2011 Charles E. Vejnar
#
# This is free software, licensed under the GNU General Public License v3.
# See /LICENSE for more information.
#

"""Probability based on binomial distribution feature."""

import math

from . import seed
from . import prob

def binomial_cdf(k, n, p):
    # Exact solution using log to avoid float overflow errors (https://stackoverflow.com/a/45869209)
    cdf = 0
    b = 0
    for k in range(k+1):
        if k > 0:
            b += math.log(n-k+1) - math.log(k)
        log_pmf_k = b + k * math.log(p) + (n-k) * math.log(1-p)
        cdf += math.exp(log_pmf_k)
    return cdf

class mmProbBinomial(seed.mmSeed):
    def eval_prob_binomial(self, markov_order=None, alphabet=None, transitions=None, motif_def=None, motif_upstream_extension=None, motif_downstream_extension=None):
        """Computes the *P.over binomial* score.

           :param markov_order: Markov Chain order
           :type markov_order: int
           :param alphabet: List of nucleotides to consider in the sequences (others get filtered).
           :type alphabet: list
           :param transitions: Transition matrix of the Markov Chain model
           :type transitions: list
           :param motif_def: 'seed' or 'seed_extended' or 'site'.
           :type motif_def: str
           :param motif_upstream_extension: Upstream extension length.
           :type motif_upstream_extension: int
           :param motif_downstream_extension: Downstream extension length.
           :type motif_downstream_extension: int"""
        # Parameters
        if markov_order is None:
            markov_order = Defaults.markov_order
        if alphabet is None:
            try:
                alphabet = Defaults.alphabet
            except AttributeError:
                alphabet = list(set(self.target_seq))
        if transitions is None:
            transitions = prob.get_transitions(self.target_seq, alphabet, markov_order)
        if motif_upstream_extension is None:
            motif_upstream_extension = 0
        if motif_downstream_extension is None:
            motif_downstream_extension = 0
        # Reset
        self.prob_binomials = []
        # Compute
        for its in range(len(self.end_sites)):
            end_site = self.end_sites[its]
            # start_motif and end_motif are sequence coordinates => 1-based
            start_motif, end_motif = seed.get_motif_coordinates(end_site, motif_def, self.pairings[its], motif_upstream_extension, motif_downstream_extension, self.min_target_length)
            motif = self.target_seq[start_motif-1:end_motif]
            #self.prob_binomials.append(1. - sp.stats.binom.cdf(self.target_seq.count(motif), self.len_target_seq-len(motif)+1, prob_motif(motif, alphabet, markov_order, transitions)))
            self.prob_binomials.append(1. - binomial_cdf(self.target_seq.count(motif), self.len_target_seq-len(motif)+1, prob.prob_motif(motif, alphabet, markov_order, transitions)))

    def get_prob_binomial(self, method=None):
        """*P.over binomial* score with default parameters.

           :param method: Method name used to combine target scores (Example: 'min').
           :type method: str"""
        if method is None:
            method = 'min'
        if hasattr(self, 'prob_binomials') is False:
            self.eval_prob_binomial()
        if method == 'min':
            self._prob_binomial = min(self.prob_binomials)
        elif method == 'prod':
            self._prob_binomial = 1.
            for p in self.prob_binomials:
                self._prob_binomial *= p
        return self._prob_binomial

    @property
    def prob_binomial(self):
        """*P.over binomial* score with default parameters."""
        return self.get_prob_binomial()

class Defaults(object):
    markov_order = 1
