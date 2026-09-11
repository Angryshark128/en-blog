---
title: "Where Distributed Systems Complexity Comes From"
date: 2026-09-11
draft: false
tags: ["distributed-systems", "consensus", "replication", "architecture"]
slug: distributed-systems-complexity
description: "The complexity of distributed systems reduces to three root problems: space, time, and consensus. Why each one resists a simple answer, how they stack, and what that means when you pick a protocol."
---

Three machines in a rack are still three machines. They become a distributed system when they have to finish one job together, and that requirement is where the trouble starts.

On a single machine you get three things for free. Every thread shares the same memory, so a write lands and everyone sees it. One clock puts every event in order. One lock protects the shared state.

Move that job across a network and all three disappear.

Everything hard about distributed systems comes from three root problems: space, time, and consensus. Space shows up first and you notice it. Time is quieter, and you misread it. Consensus is what you get once the first two pile up.

{{< diagram "three-problems.svg" "Space and time become consensus" >}}

## Space: the data lives in more than one place

Sharing a variable inside one process costs nothing. Run the same code on two machines and each node holds a piece of the truth. No node holds all of it.

### Replication: who gets to write

Let every node write and two of them will accept conflicting writes for the same key. Neither has heard from the other yet, so both believe they are right. Now you need a rule for that conflict.

Restrict writes to one leader and you inherit a different set of problems. Then the leader dies, and you own the seconds that follow. You also have to decide which reads may go to a follower that lags behind.

Single-leader, multi-leader, and leaderless replication are three answers to the write question. Each one leaves you a different set of failures.

{{< diagram "replication.svg" "Who may write" >}}

### Partitioning: where data goes

The dataset outgrows one disk. Split by key range and the ranges go out of balance as traffic shifts. Split by hash and each node gets a similar share of writes. Range scans get slower, and a query that needs rows from two partitions pays a network hop.

{{< diagram "partitioning.svg" "Range versus hash" >}}

The two problems multiply. One node can lead one partition and follow another, so the replication policy has to match the partition layout. The topology you draw on a whiteboard becomes a set of rules every node has to agree on.

## Time: order stops being obvious

Code on one machine gives you a total order. The line `a = 1` finishes before the line `b = a + 1` reads it, because the hardware guarantees that.

Across machines there's no global clock. Two machines drift apart and NTP holds them within milliseconds, which is slow when you handle thousands of operations per second. The network reorders messages on top of that. You send A, then B, and the receiver gets B first.

Read a timestamp and you still can't say which event happened first.

### Clocks that count events

Drop wall-clock time and ask a smaller question instead. Compare two events: did one cause the other?

If A causes B, then A is earlier. If neither causes the other, the two ran concurrently. A logical clock records that relation and gives you a partial order.

One counter carries one number, so it can't separate concurrency from causation. Vector clocks fix that. Each node keeps one counter per node. Comparing two vectors tells you whether one event caused the other, or whether the two just happened in parallel.

{{< diagram "causality.svg" "Causal, or concurrent" >}}

The price grows with the cluster. A 500-node system attaches 500 counters to every message, and trimming old entries means accepting wrong answers.

### The consistency spectrum

Ordering uncertainty is why you choose from a spectrum of consistency models.

Linearizability makes every operation look like it took effect at one instant on one machine. Sequential consistency drops the real-time requirement and keeps one global order. Causal consistency orders causes before effects and ignores the rest. Eventual consistency promises that replicas converge once writes stop, and stays quiet about when.

{{< diagram "consistency-spectrum.svg" "Strong to weak" >}}

Each step down that ladder buys you latency and availability, and costs you a rule you can reason about.

## Consensus: agreement is the hard part

Stack space on top of time and you get the problem distributed systems are famous for.

You run into consensus in a lot of disguises. A cluster elects a leader. A transaction spans two databases and has to commit on both or neither. Two clients want the same row locked.

Every one of those reduces to the same requirement. A group of nodes that don't trust each other, talking over a network that drops and delays messages, has to agree on one value.

### The FLP result

In an asynchronous system, if one node can crash, no deterministic protocol can guarantee consensus.

The word that matters is deterministic. The theorem covers protocols that never give a wrong answer. Protocols that get it right with high probability sit outside it, and that gap is where Paxos and Raft live. Both use a quorum and randomized timeouts, so they finish in practice without ever being certain in theory.

### Paxos, Raft, and ZAB

Paxos is correct and hard to implement. Raft splits the same problem into leader election, log replication, and safety, which makes the protocol teachable. ZAB drives ZooKeeper and takes a similar route with ordering guarantees on top.

All three need a majority to get anything done. A five-node cluster survives two failures. Split it 3 to 2 and the minority side can't serve writes.

{{< diagram "quorum.svg" "Majority writes, minority waits" >}}

### Distributed transactions

Two-phase commit asks every participant to prepare, then tells everyone to commit. That window between the two phases is the weak point. If the coordinator dies after the prepares, participants sit there holding locks.

{{< diagram "two-phase-commit.svg" "Prepare, vote, commit" >}}

Three-phase commit adds a timeout step that shrinks the window without closing it. Saga and TCC commit each step and define a compensating action for it, which trades isolation for availability. One step fails and you spend the following week untangling a state that no single snapshot explains.

## The three problems stack

Space, time, and consensus don't sit side by side. Space is the one you notice, because a node hands back stale data and the gap shows up in a request.

Time is harder to catch. The bugs it causes look like space bugs until you check clock skew or measure how far behind a follower is.

Consensus needs both before it bites. Agreement only gets hard once the data lives in several places and the messages arrive in an order you can't predict.

That explains the size of the toolbox. Vector clocks, quorums, consistent hashing, leader election, compensation protocols. Different angles on one question: several machines have to finish one job, and each machine sees only its own local state.

Next time a design review stalls on gossip versus Raft, or on two-phase commit versus Saga, name the problem you are paying for.

With replication you decide who writes. With partitioning you decide where data lives. With time you decide whether ordering matters. With consensus you decide what the group accepts.
