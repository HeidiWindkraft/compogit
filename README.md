# compogit
Poor man's git submodules

This project is basically about playing around with `git rebase -i`.

[sic](https://github.com/HeidiWindkraft/sic) has some components which are ready to be pushed,
while other components aren't.
Unfortunately I committed change sets which contain changes in multiple components.
As git works based on commits, you can't just push half of a commit or only a directory.
Therefore, the commits have to be split using `git rebase -i`.
`compogit` is meant to automate this.

If you have different components in your repository,
you should probably create a git repository for each component.

## Usage

(work in progress)

Create a directory called `compogit` or `.compogit` in the top-level directory of
your git repository - this can be done using `compogit-init`.

Modify `compogit/compospec.json` to describe the components of your repository.
For example:
```JSON
{
	"Preprocessor": {
		"path": [ "preprocessor" ]
	},
	"Parser": {
		"path": [ "parser" ]
	}
}
```

If your last commit modified different components, you can call `compogit-split-last-unpushed-commit`
to split it.
It splits your last commit into one commit for each component, if it modified multiple components.

Optionally, specify the message, which shall be used to split your commits in `compogit/splitmessage.txt`.
For example:
```
%s (component ${compogit_component} of ${compogit_original_short_hash})
%b
```
If no `splitmessage.txt` is given, compogit just does every commit using the original message.
See [`man git-log` `/PRETTY FORMATS`](https://git-scm.com/docs/pretty-formats) for a list of placeholders.
The list of compogit placeholders is:
  - `${compogit_component}` the component which is modified by this commit
  - `${compogit_original_short_hash}` the short hash of the commit which is currently split
  - `${compogit_original_long_hash}` the full hash of the commit which is currently split
