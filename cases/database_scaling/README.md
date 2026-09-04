# Database scaling regression

This fixture tests the same generic DecisionGate machinery as the government-program case in an unrelated technical architecture domain.

The supplied benchmark establishes that Database B is 35% faster at approximately 10,000 records. Production may reach approximately 50 million records, and no production-scale benchmark is available. Choosing Database B therefore depends on an unresolved scalability assumption.

Run it from the repository root:

```bash
decisiongate evaluate --case cases/database_scaling/case.json --output build/database-scaling
```

Expected disposition: `HUMAN_VERIFY`.

This is not evidence that Database B is unsuitable. It means that the available evidence does not establish that its measured advantage generalizes to production-representative conditions.

