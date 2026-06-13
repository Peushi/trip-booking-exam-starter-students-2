# Final Exam - Distributed Systems Application Refactor

## Context

You are given a naive distributed trip-booking application.

The application is composed of several services that cooperate to book a trip:

- a trip service;
- a flight service;
- a hotel service;
- a payment service;
- a notification component;
- a database;
- a message broker.

The baseline application works in simple happy-path scenarios, but it is intentionally incomplete. It does not correctly handle several situations that appear in real distributed systems, such as concurrency, partial failure, duplicate requests, duplicate messages, inconsistent state, stale data, or state distribution.

Your task is to refactor the application by implementing selected distributed-systems concepts studied in class.

The goal is not to add random features. The goal is to improve the correctness, reliability, or scalability of the system using concepts from the course.

---

## Your task

You must implement **at least 4 accepted distributed-systems concepts** in the provided application.

You must choose concepts according to the category requirements below:

1. **two concepts from Category A - Local correctness**
2. **one concept from Category B - Distributed workflow or messaging**
3. **one concept from Category C - Communication, consistency, or scaling**

Additional concepts may come from any category and may grant bonus points, but only if the 4 required concepts are already valid.

At most two additional concepts will be considered for bonus.

Bonus concepts are ignored if the 4 required concepts are not already accepted.

> A concept is valid only if it is implemented, integrated, documented, and demonstrated.
>
> A concept is valid only if it produces an observable, meaningful change in the application's behavior.
>
> Purely cosmetic changes, documentation-only changes, unused code, or code that is not demonstrated do not count.

You may not claim the same code change or the same observed behavior as two different concepts.

Some concepts naturally require supporting mechanisms. For example, a row lock usually requires a transaction, and a saga may require storing intermediate states. These supporting mechanisms do not automatically count as additional concepts.

To claim two concepts, you must show two distinct intentions and two distinct observable behaviors.

Examples:

- Valid: a database transaction prevents half-created local state after a forced failure, and a row-level lock prevents concurrent overbooking. Each concept has its own test or demo.
- Not valid: claiming "saga" and "compensation" separately when the group only implemented one try/except block and one failure case.

## Completeness of a concept

A concept is counted at the application level, not per endpoint, file, or service.

When you claim a concept, you must apply it to all equivalent places in the application where that concept is relevant and feasible. For example, if you claim a concurrency-control concept for inventory reservation, it should protect both flight seats and hotel rooms if both still have the same race condition.

Applying the same mechanism in several services or endpoints normally counts as one concept, not several concepts.

If you intentionally apply a concept only to part of the system, you must explain why the remaining similar cases are out of scope. A partial implementation may receive partial credit.

---

# Category A - Local correctness

Choose **two** concepts from this category.

You must choose:

- at least one concept from A1 - Integrity and atomicity;
- at least one concept from A2 - Concurrency control.

These concepts focus on making one service correct even when several requests happen at the same time or when invalid state could be created.

## A1 - Integrity and atomicity

Possible choices:

- database transaction;
- database constraints;

## A2 - Concurrency control

Possible choices:

- pessimistic locking;
- optimistic locking;
- isolation-level handling;
- conflict detection and retry.

You may combine several mechanisms in the code, but you must clearly identify which two concepts you are claiming and demonstrate a different behavior for each one.

Your implementation should protect a clear local invariant.

Examples of local invariants:

- the number of available seats must not become negative;
- the number of available rooms must not become negative;
- the same resource must not be reserved twice incorrectly;
- a partially failed local operation must not leave invalid state.

Do not implement only an in-memory solution unless you can justify why it is sufficient in the context of the application.

---

# Category B - Distributed workflow or messaging

Choose **one** concept from this category.

These concepts focus on what happens when several services must cooperate, or when asynchronous messages are delivered, retried, duplicated, or lost.

Possible choices:

- saga with a durable state machine;
- compensation path for a distributed operation;
- TCC: Try / Confirm / Cancel;
- simplified two-phase commit, with clearly documented limitations;
- duplicate-message handling;

Your implementation should address a situation where one service succeeds and another service fails, or where an asynchronous message is processed incorrectly.

Examples of distributed problems:

- a flight is booked but the hotel reservation fails;
- a hotel is reserved but the payment fails;
- a trip is marked as confirmed but the notification event is not published;
- the same message is consumed twice;
- compensation fails and the system must remember it;
- a long-running trip booking operation needs explicit states.

You are not expected to solve all distributed-workflow problems in the application.
For the concept you choose, define one precise failure scenario and handle it correctly.

Your implementation must make the final state of the system easier to reason about than in the baseline application.

---

# Category C - Communication, consistency, or scaling

Choose **one** concept from this category.

These concepts focus on communication models, repeated requests, stale data, distributed state, or data placement.

Possible choices:

- RPC-style communication;
- GraphQL gateway;
- idempotency key for a client request;
- retry-safe remote call;
- caching with a freshness policy;
- sharding;
- read-your-writes behavior;
- replica-lag simulation;
- quorum simulation;
- hotspot detection or mitigation.

Your implementation should show a real trade-off.

For concepts with a limited implementation surface, such as an idempotency key, the grading expectation is stricter: the implementation must be complete, durable, and demonstrated under the failure or retry scenario it claims to handle.

For example, an idempotency key should normally include persistent key storage, duplicate-request detection, a defined behavior for repeated requests, and a test or demo showing that duplicate client submissions do not create duplicate side effects.

A retry-safe remote call must demonstrate that retries do not create duplicate side effects.

Examples of trade-offs:

- a cache can improve read performance but may return stale data;
- sharding can distribute data but makes some queries harder;
- retries can improve availability but may duplicate side effects;
- GraphQL can simplify the client but may hide backend fan-out;
- reading from a replica may be faster but may show old data;
- a quorum can improve consistency but may reduce availability during failures.

A purely cosmetic API change is not enough.

---

# Required deliverables

Your repository must include the following elements.

## 1. Working application

The application must still run after your changes.

At minimum, the following must work:

```bash
docker compose up --build
```

The main services must start successfully.

The basic happy-path trip booking scenario must still work unless your design intentionally changes the expected API. If you change the API, you must document the new behavior.

In all cases, your scripts must be runnable on Linux.
Your submitted application should run through Docker Compose whenever possible.

---

## 2. Clear README update

Update the project `README.md` with a section named:

```markdown
## Exam refactor
```

In that section, include a table like this:

```markdown
| Concept | Category | Main files modified | How to test it |
|---|---|---|---|
| ... | ... | ... | ... |
```

Keep this explanation short and technical.

Do not write a long essay.

---

## 3. One concept card per implemented concept

Create one markdown file per implemented concept in:

```text
docs/concepts/
```

Use the following naming convention:

```text
docs/concepts/concept-1.md
docs/concepts/concept-2.md
docs/concepts/concept-3.md
docs/concepts/concept-4.md
docs/concepts/concept-N.md
```

Each concept card must follow this format:

```markdown
# Concept name

## Category

A, B, or C.

If the concept belongs to Category A, specify A1 or A2.

## Problem

What problem in the baseline application does this concept address?

## Invariant or guarantee

What property should now hold?

## Modified files

List the main files you changed.

## Behavior before

Briefly describe what could go wrong before your change.

## Behavior after

Briefly describe what should happen now.

## How to test

Give the command or scenario used to verify your implementation.

## Limitation

What does your solution not solve?
```

Be precise. Avoid vague statements such as "the system is more reliable now."

---

## 4. Test or demo scenario

For each implemented concept, provide at least one way to verify the behavior.

This can be:

- an automated test;
- a script in the `scripts/` directory;
- a documented manual scenario;
- a short command sequence.

Automated tests are preferred.

Your verification must show more than the happy path. It should exercise the situation your concept is supposed to improve.

Examples of acceptable verification scenarios:

- concurrent requests;
- duplicate client request;
- service failure;
- payment failure;
- message redelivery;
- stale read;
- cache invalidation;
- wrong shard access.

A concept without a test or demo scenario will receive limited credit.

---

# Submission requirements

Your final submission must contain:

```text
README.md updated
docs/concepts/concept-1.md
docs/concepts/concept-2.md
docs/concepts/concept-3.md
docs/concepts/concept-4.md
one additional concept card for each bonus concept, if any
working source code
test or demo scenario for each concept
```

You may add new files and directories if needed.

You may modify the application architecture if your concept requires it, but the result must remain understandable and runnable.

---

# Constraints

## Keep the application understandable

This is a distributed-systems exam, not a framework competition.

Prefer a simple, correct implementation over a complex implementation that is difficult to explain.

Do not introduce unnecessary infrastructure.

---

## Do not bypass the distributed-systems problem

You should not solve the assignment by removing the distributed nature of the application.

For example, do not:

- merge all services into one service;
- move all data into one shared table used directly by all services;
- remove remote calls instead of handling them;
- remove the message broker if your chosen concept concerns messaging;
- hardcode success responses instead of handling real state.

The system should remain a distributed application.

---

## Do not fake correctness

Your code must actually enforce or demonstrate the concept you selected.

For example:

- if you claim to handle duplicate requests, repeated requests must be tested;
- if you claim to prevent overbooking, concurrent booking attempts must be tested;
- if you claim to implement a saga, intermediate and failure states must exist;
- if you claim to handle duplicate messages, duplicate delivery must be tested;
- if you claim to implement caching, stale data must be considered;
- if you claim to implement sharding, there must be a routing rule.

---

## External resources

You may use:

- course material;
- official documentation;
- online resources;
- AI assistance:
  - brainstorming, debugging help, documentation help, and test generation are allowed;
  - generating the implementation of the selected exam concepts is not allowed.

You are responsible for every line of code you submit.
Code that you cannot explain may be treated as non-validated.

Do not submit code that you cannot explain or debug.

If you use a significant external source or AI, mention it briefly in the README. Failing to do so will result in a penalty when detected.

---

# Suggested working method

A recommended approach is:

1. Run the original application.
2. Run the provided demo scripts.
3. Identify baseline weaknesses.
4. Choose your concepts.
5. Implement one concept at a time.
6. Add a test or demo for each concept.
7. Update the README and concept cards.
8. Verify the whole application still runs.

Do not wait until the end to test integration.

---

# Evaluation focus

Your implementation will be evaluated according to the following criteria:

## Correctness

Does the implementation actually address the problem it claims to address?

## Relevance

Is the implemented mechanism related to the distributed-systems concept selected?

## Evidence

Is there a test or demo showing the behavior?

## Integration

Does the application still run as a coherent system?

## Simplicity

Is the solution understandable and appropriate for the problem?

## Limitations

Do you identify what your solution does not solve?

---

# Important reminder

You are not expected to make the whole application production-ready.

You are expected to select **at least four** meaningful weaknesses and improve them using concepts from the course.

A small, well-tested, well-explained refactor is better than a large, unclear, untested rewrite.
