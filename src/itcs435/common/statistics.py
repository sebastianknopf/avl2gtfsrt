import math

def softmax(scores: list):
    max_score: float = max(scores)
    exp_scores: list = [math.exp(s - max_score) for s in scores]
    sum_exp: float = sum(exp_scores)

    return [e / sum_exp for e in exp_scores]

def bayesian(prior: dict, likelihood: dict, normalized: bool = False, alpha: float = 1.0) -> dict:
    
    # extend likelihood values for all keys in prior
    for k in [x for x in prior.keys() if x not in likelihood]:
        likelihood[k] = 0.0

    # ensure that prior and likelihood are sorted both by their key 
    prior = dict(sorted(prior.items()))
    likelihood = dict(sorted(likelihood.items()))

    # normalize all values for likelihood using softmax activation
    if not normalized:
        likelihood_values: list = list(likelihood.values())
        likelihood_values = softmax(likelihood_values)

    # extract all prior values
    prior_values: list = list(prior.values())

    # calulate update according to the bayesian rule
    unnormalized_posterior: list = [
        p * (l ** alpha) for p, l in zip(prior_values, likelihood_values)
    ]

    total_posterior: float = sum(unnormalized_posterior)

    # normalize posterior
    if total_posterior == 0.0:
        posterior: list = [0.0 for _ in unnormalized_posterior]
    else:
        posterior: list = [u / total_posterior for u in unnormalized_posterior]

    posterior_dict: dict = dict()
    for i, (k, _) in enumerate(prior.items()):
        posterior_dict[k] = posterior[i]

    return posterior_dict