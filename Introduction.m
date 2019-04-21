%%% INTRODUCTION %%%
%% MATLAB is expressed in matrices
% e.g. vector = [1 2 3] --> comma is not necessary
% e.g. m = [1 2; 3 4] --> semicolon is necessary to introduce a new row
% m(i,j) --> i is the row, j is the column
% The colon syntax, e.g. m(1,:), is used to extract all the elements
% The semi-colon syntax is used to suppress the output in the command window
% Index always starts from 1, instead of 0 (as in Python)

%% Matrix Operators
% +, - is used for matrix addition and subtraction
% * is used for matrix multiplication
% \ is used for matrix division --> inv(A)*B
% Regardless the operator, the matrix dimensions must agree
% y' is the transpose of y
% The classical BODMAS applies

%% Element-wise Operators
% .* is used for element-wise multiplication
% ./ is used for element-wise division
% == is used for comparison of two expressions. If same, returns 1. Else 0

%% Functions
% disp(x) outputs the values of x in command window
% x = [a1 a2 a3], y = [b1 b2 b3] 
% --> Dot product of x and y = dot (x,y) = a1b1 + a2b2 + a3b3 
% --> Cross product of x and y = cross(x,y), where c1 = a2b3 ? a3b2, c2 = a3b1 ? a1b3, c3 = a1b2 ? a2b1
% sin, cos and tan apply and return answers in radians
% sqrt, exp and log apply
% Built-in constants, e.g. pi and i (which is sqrt(-1))
% Identity matrix --> e.g. eye(2)
% Zero matrix --> zeros(i,[j]), where j is optional
% Ones matrix --> ones(i, [j]), where j is optional
% tilda is the NOT operator in MATLAB
% det(A) returns the determinant of matrix A
% [V D] = eig(A) returns the eignevalues of diagnoal matrix D and eigenvectors V
% Creating functions --> function [output arguments] = name_of_program_file(input arguments)

%% Loops and Decision Trees
% Regardless of loops and decision trees, we need to append end to denote the end of the loop/decision tree
% for x = X --> loops through each element in matrix X
% break is used to break a loop

%% Data types
% struct is similar to dictionary in Python.
% --> To initialize a struct, my_struct = struct('key1', 'value1', 'key2', 'value2', ...)
% --> To append an existing struct with key and values: setfield(my_struct, 'gender', 'f') 

%% Data plots
% Invoke plot([x],y) --> Note that both x and y must have the same size
% We can also invoke the plot function to plot multi-curves, i.e. plot(x1,y1,x2,y2,...)
% We can use line style to denote the different curves, i.e. plot(x1,y1,'--', x2,y2,'.',...)
% linspace(start,end,no.of points) is useful to generate pre-determined points

% To perform a barplot, use bar([x], y)
% To perform a histogram, use hist(x, bins) --> Note that MATLAB uses the number of x values as bins by default
% To perform a pie chart, use pie(x)
% To perform a scatter plot, use scatter(x,y)

% In the earlier example, we show multi-curves in the same plot. To show them as different plots, i.e. subplots, we use
% --> subplot(rows,cols,firstcurve), subplot(rows,cols,seccurve)...
% --> Note that the rows must be equal to the number of subplots. Cols can be defaulted as 1
% To perform a surface plot, use surf(x)
% To perform a contour plot, use contour(x)

% To give a title, labels to the plot, use title('name'), xlabel('name'), ylabel('name')

%% Data import/export
% importdata()
% xlsread(filename) and xlswrite(filename, content) are used to read/write Excel files
% csvread(filename) and csvwrite(filename, content) are used to read/write csv files
% save('my_workspace.mat') will save all the variables in the workspace (see left)
% load('my_workspace.mat') will load all the variables into the workspace (see left)

%% Publish Report
% We can click Publish to publish the codes/plots as a html report

%% Probability 
% randn(n) --> Returns n by n matrix of std normally distributed random numbers
% randi(x,n) --> Returns n by n matrix with random integers between 1 and x (both numbers inclusive)
% rand(n) --> Returns n by n matrix of uniformly distributed random numbers between 0 and 1 
% mean(X) --> Returns the expected value of X
% var(X) --> Returns the unbiased variance of X 
% jbtest(X) --> Test that determines whether we reject the null hypothesis of normal distribution
% ttest(X1,X2) --> Test that determines whether the two distributions X1 and X2 are different