import math

def softmax(scores: list):
    if len(scores) == 0:
        return []

    max_score: float = max(scores)
    exp_scores: list = [math.exp(s - max_score) for s in scores]
    sum_exp: float = sum(exp_scores)

    return [e / sum_exp for e in exp_scores]

def bayesian_update(prior: dict, likelihood: dict, normalized: bool = False, alpha: float = 1.0) -> dict:
    
    # normalize all values for likelihood using softmax activation
    if not normalized:
        likelihood_values: list = list(likelihood.values())
        likelihood_values = softmax(likelihood_values)

        for i, (k, _) in enumerate(likelihood.items()):
            likelihood[k] = likelihood_values[i]
    
    # remove keys from prior if the are not considered as 
    # trip candidates in the current update anymore
    # also add new candidates to prior if they are in likelihood
    prior = {k: v for k, v in prior.items() if k in likelihood}

    for k, v in likelihood.items():
        if k not in prior:
            prior[k] = v

    # ensure that prior and likelihood are sorted both by their key 
    prior = dict(sorted(prior.items()))
    likelihood = dict(sorted(likelihood.items()))

    # extract all values
    likelihood_values: list = list(likelihood.values())
    prior_values: list = list(prior.values())

    # calulate update according to the bayesian rule
    unnormalized_posterior: list = [
        p * (l ** alpha) for p, l in zip(prior_values, likelihood_values)
    ]

    total_posterior: float = sum(unnormalized_posterior)

    # normalize posterior and re-create dict
    if total_posterior == 0.0:
        posterior: list = [0.0 for _ in unnormalized_posterior]
    else:
        posterior: list = [u / total_posterior for u in unnormalized_posterior]

    posterior_dict: dict = dict()
    for i, (k, _) in enumerate(prior.items()):
        posterior_dict[k] = posterior[i]

    return posterior_dict